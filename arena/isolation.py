"""Runtime isolation profiles and fail-closed admission.

BuilderWars v1 has one implemented executor: a subprocess with bounded pipes,
scratch cwd, and an environment allowlist. It is useful for maintainer-authored
entrants, but it is not an OS capability boundary. This module makes that fact a
machine-readable preflight decision rather than a prose-only caveat.
"""

from copy import deepcopy

ISOLATION_SCHEMA = "nymrel.builderwars.isolation.v1"

PROCESS_ISOLATION = {
    "schema": ISOLATION_SCHEMA,
    "mode": "process",
    "executor": "python-subprocess",
    "capability_isolation": False,
    "trusted_entrants_only": True,
    "enforced": {
        "separate_process": True,
        "scratch_working_directory": True,
        "environment_allowlist": True,
        "close_inherited_file_descriptors": True,
        "transcript_path_withheld": True,
        "per_move_wall_clock_timeout": True,
        "stdout_line_limit": True,
        "stdout_total_limit": True,
        "stderr_capture_limit": True,
        "kill_on_timeout_and_match_end": True,
    },
    "unenforced": {
        "network_egress_blocking": False,
        "filesystem_confinement": False,
        "cpu_limit": False,
        "memory_limit": False,
        "process_count_limit": False,
        "host_credential_boundary": False,
    },
    "claim": (
        "Process-isolated and capability-unconfined. Suitable only for entrants "
        "the operator already trusts to run on this host."
    ),
}

_PROFILE_KEYS = frozenset(PROCESS_ISOLATION)
_ENFORCED_KEYS = frozenset(PROCESS_ISOLATION["enforced"])
_UNENFORCED_KEYS = frozenset(PROCESS_ISOLATION["unenforced"])


class IsolationRequirementError(RuntimeError):
    """The requested execution boundary is unavailable before a match starts."""

    def __init__(self, reason, requested_mode="process"):
        super().__init__(reason)
        self.reason = reason
        self.requested_mode = requested_mode

    def to_json(self):
        return {
            "error": "isolation_requirement_unsatisfied",
            "reason": self.reason,
            "requested_mode": self.requested_mode,
            "available_mode": "process",
            "required": {"capability_isolation": True},
            "available": {"capability_isolation": False},
            "match_started": False,
        }


def resolve_isolation(mode="process", require_capability_isolation=False):
    """Return the exact profile or fail before any match side effect.

    A future executor must earn a new mode through implementation and evidence.
    Passing an unknown name can never silently fall back to process mode.
    """

    if mode != "process":
        raise IsolationRequirementError(
            "requested isolation mode is not implemented",
            requested_mode=mode,
        )
    profile = deepcopy(PROCESS_ISOLATION)
    if require_capability_isolation and not profile["capability_isolation"]:
        raise IsolationRequirementError(
            "capability isolation was required, but process mode does not enforce it",
            requested_mode=mode,
        )
    return profile


def _exact_keys(value, expected, label):
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(
            f"{label} fields are not exact "
            f"(missing: {', '.join(missing) or 'none'}; "
            f"unknown: {', '.join(unknown) or 'none'})"
        )


def validate_isolation_profile(profile):
    """Reject any profile that differs from the implemented process boundary.

    This validator deliberately checks the exact field and control sets. A
    profile cannot become more impressive by deleting an unenforced control,
    adding an unimplemented control, or changing a prose claim while retaining
    the same schema version. Any real executor change requires a new reviewed
    profile and, when semantics change, a schema version change.
    """

    if not isinstance(profile, dict):
        raise ValueError("isolation profile must be an object")
    _exact_keys(profile, _PROFILE_KEYS, "isolation profile")

    expected_scalars = {
        "schema": ISOLATION_SCHEMA,
        "mode": "process",
        "executor": "python-subprocess",
        "capability_isolation": False,
        "trusted_entrants_only": True,
        "claim": PROCESS_ISOLATION["claim"],
    }
    for field, expected in expected_scalars.items():
        if profile[field] != expected:
            raise ValueError(
                f"isolation profile {field} does not match the implemented process boundary"
            )

    enforced = profile["enforced"]
    unenforced = profile["unenforced"]
    if not isinstance(enforced, dict) or not isinstance(unenforced, dict):
        raise ValueError("isolation controls must be objects")
    _exact_keys(enforced, _ENFORCED_KEYS, "enforced isolation controls")
    _exact_keys(unenforced, _UNENFORCED_KEYS, "unenforced isolation controls")
    if enforced != PROCESS_ISOLATION["enforced"]:
        raise ValueError("enforced controls do not match the implemented process boundary")
    if unenforced != PROCESS_ISOLATION["unenforced"]:
        raise ValueError("unenforced controls do not match the implemented process boundary")
    if set(enforced) & set(unenforced):
        raise ValueError("isolation controls may not be both enforced and unenforced")
    return deepcopy(profile)
