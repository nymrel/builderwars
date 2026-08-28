"""Declarative BuildWars build-off contracts.

BuildWars is the artifact-review format inside the BuilderWars platform.  It is
deliberately separate from the AgentWars game/replay evidence class.
"""

from .contracts import (
    BuildWarsContractError,
    candidate_projection,
    canonical_bytes,
    decode_strict,
    digest,
    seal_buildoff,
    validate_challenge,
    validate_entry,
    validate_judgment,
    validate_receipt,
    verify_receipt,
)

__all__ = (
    "BuildWarsContractError",
    "candidate_projection",
    "canonical_bytes",
    "decode_strict",
    "digest",
    "seal_buildoff",
    "validate_challenge",
    "validate_entry",
    "validate_judgment",
    "validate_receipt",
    "verify_receipt",
)
