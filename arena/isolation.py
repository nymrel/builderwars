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


def validate_isolation_profile(profile):
    """Reject profiles that overstate the only implemented executor."""

    if not isinstance(profile, dict):
        raise ValueError("isolation profile must be an object")
    if profile.get("schema") != ISOLATION_SCHEMA:
        raise ValueError("isolation profile schema mismatch")
    if profile.get("mode") != "process":
        raise ValueError("only process isolation is implemented")
    if profile.get("capability_isolation") is not False:
        raise ValueError("process mode may not claim capability isolation")
    enforced = profile.get("enforced")
    unenforced = profile.get("unenforced")
    if not isinstance(enforced, dict) or not isinstance(unenforced, dict):
        raise ValueError("isolation controls must be objects")
    if any(value is not True for value in enforced.values()):
        raise ValueError("enforced controls must be explicit true values")
    if any(value is not False for value in unenforced.values()):
        raise ValueError("unenforced controls must be explicit false values")
    overlap = set(enforced) & set(unenforced)
    if overlap:
        raise ValueError("isolation controls may not be both enforced and unenforced")
    return deepcopy(profile)
