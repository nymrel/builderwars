"""Framework-independent hosted control-plane reference for AgentWars.

This package is deliberately separate from the customer-local provider hub.
It stores no provider credential or provider session and executes no entrant or
model code.  It demonstrates only account-to-runner key binding, signed
transport, durable fixture-job state, and an allow-list deterministic result
projection.
"""

from provider_hub_hosted.handlers import HostedControlPlane
from provider_hub_hosted.store import HostedControlPlaneStore, HostedStoreError
from provider_hub_hosted.verify import (
    IncomingSignedRequest,
    SignedRequestError,
    VerifiedRunnerRequest,
    verify_signed_request,
)

__all__ = [
    "HostedControlPlane",
    "HostedControlPlaneStore",
    "HostedStoreError",
    "IncomingSignedRequest",
    "SignedRequestError",
    "VerifiedRunnerRequest",
    "verify_signed_request",
]
