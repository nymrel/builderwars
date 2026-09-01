"""Fail-closed admission contract for executable arena entrants.

The arena/1 process boundary is useful for deterministic local matches, but it
is not a capability sandbox.  This module keeps *where and under whose control*
an entrant is executed separate from the entrant's self-declared model or
execution claim.

Only two local scopes are admitted by v1.  Hosted untrusted code is a named,
parseable scope so callers cannot turn an unsupported request into a local run
by omission.  It is always refused before output directories or processes are
created.
"""

from copy import deepcopy


PROTOCOL = "builderwars/entrant-admission/1"

REFERENCE_REVIEWED_LOCAL_V1 = "reference_reviewed_local_v1"
CUSTOMER_CONTROLLED_LOCAL_V1 = "customer_controlled_local_v1"
EXTERNAL_UNTRUSTED_HOSTED_V1 = "external_untrusted_hosted_v1"

ADMITTED_EXECUTION_SCOPES = frozenset(
    {REFERENCE_REVIEWED_LOCAL_V1, CUSTOMER_CONTROLLED_LOCAL_V1}
)
EXECUTION_SCOPES = frozenset(
    {*ADMITTED_EXECUTION_SCOPES, EXTERNAL_UNTRUSTED_HOSTED_V1}
)

_ADMISSION_RECORDS = {
    REFERENCE_REVIEWED_LOCAL_V1: {
        "protocol": PROTOCOL,
        "scope": REFERENCE_REVIEWED_LOCAL_V1,
        "decision": "ADMITTED_LOCAL_ONLY",
        "source_authority": "repository_reviewed_reference",
        "execution_location": "operator_controlled_local_host",
        "platform_hosted": False,
        "public_uploaded_code": False,
        "capability_isolation_attested": False,
    },
    CUSTOMER_CONTROLLED_LOCAL_V1: {
        "protocol": PROTOCOL,
        "scope": CUSTOMER_CONTROLLED_LOCAL_V1,
        "decision": "ADMITTED_LOCAL_ONLY",
        "source_authority": "customer_controlled_unreviewed",
        "execution_location": "customer_controlled_local_host",
        "platform_hosted": False,
        "public_uploaded_code": False,
        "capability_isolation_attested": False,
    },
}


class UnsupportedEntrantExecution(ValueError):
    """The requested execution scope cannot be run by the current host."""

    code = "UNSUPPORTED_UNTRUSTED_EXECUTION"

    def __init__(self, scope):
        super().__init__(
            f"{self.code}: {scope!r} requires independently verified OS capability "
            "isolation; arena/1 admits local-only execution and refused before side effects"
        )
        self.scope = scope


def require_execution_scope(scope):
    """Validate and admit one exact v1 execution scope.

    The return value is safe to bind directly into a transcript header.  A copy
    is returned so callers cannot mutate the module-level policy record.
    """

    if not isinstance(scope, str) or scope not in EXECUTION_SCOPES:
        raise ValueError(
            "execution_scope must be exactly one of: " + ", ".join(sorted(EXECUTION_SCOPES))
        )
    if scope == EXTERNAL_UNTRUSTED_HOSTED_V1:
        raise UnsupportedEntrantExecution(scope)
    return deepcopy(_ADMISSION_RECORDS[scope])
