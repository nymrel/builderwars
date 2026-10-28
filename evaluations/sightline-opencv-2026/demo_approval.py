"""One-use approval gate for the isolated Sightline demonstration fixture.

This is a demonstration control, not an authentication or production-execution
system. The Sightline proposal engine remains unable to perform an action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


DEMO_ACTION = "restore_injected_featured_receipt_visibility"
DEMO_SCOPE = "single_temporary_browser_dom_fixture"


@dataclass(frozen=True)
class DemoApproval:
    action: str
    scope: str
    findings_sha256: str
    candidate_sha256: str
    actor: Literal["automated_demo_operator"]
    human_approval_observed: Literal[False] = False
    production_authority: Literal[False] = False


class DemoApprovalGate:
    """Bind one explicit demo event to one measured candidate and proposal."""

    def __init__(self, *, findings_sha256: str, candidate_sha256: str) -> None:
        for value in (findings_sha256, candidate_sha256):
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("exact lowercase SHA-256 digests required")
        self.findings_sha256 = findings_sha256
        self.candidate_sha256 = candidate_sha256
        self._approval: DemoApproval | None = None
        self._consumed = False

    def record_demo_operator_event(self) -> dict[str, object]:
        if self._approval is not None or self._consumed:
            raise PermissionError("demo approval may be recorded once")
        self._approval = DemoApproval(
            action=DEMO_ACTION,
            scope=DEMO_SCOPE,
            findings_sha256=self.findings_sha256,
            candidate_sha256=self.candidate_sha256,
            actor="automated_demo_operator",
        )
        return asdict(self._approval)

    def consume(self, *, action: str, current_candidate_sha256: str) -> DemoApproval:
        if self._approval is None:
            raise PermissionError("explicit demo operator approval is required")
        if self._consumed:
            raise PermissionError("demo approval has already been consumed")
        if action != DEMO_ACTION:
            raise PermissionError("action is outside the approved demo scope")
        if current_candidate_sha256 != self.candidate_sha256:
            raise PermissionError("candidate changed after the diagnostic decision")
        self._consumed = True
        return self._approval
