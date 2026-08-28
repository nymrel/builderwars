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
from .lifecycle import (
    BuildWarsLifecycleError,
    append_lifecycle_event,
    assert_new_use_allowed,
    compare_lifecycle_logs,
    lifecycle_fingerprint,
    lifecycle_genesis_hash,
    make_lifecycle_event,
    replay_lifecycle,
    verify_suppression,
)

__all__ = (
    "BuildWarsContractError",
    "BuildWarsLifecycleError",
    "append_lifecycle_event",
    "assert_new_use_allowed",
    "candidate_projection",
    "canonical_bytes",
    "compare_lifecycle_logs",
    "decode_strict",
    "digest",
    "lifecycle_fingerprint",
    "lifecycle_genesis_hash",
    "make_lifecycle_event",
    "replay_lifecycle",
    "seal_buildoff",
    "validate_challenge",
    "validate_entry",
    "validate_judgment",
    "validate_receipt",
    "verify_receipt",
    "verify_suppression",
)
