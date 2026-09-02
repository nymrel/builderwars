"""Framework-independent hosted control-plane reference for AgentWars.

This package is deliberately separate from the customer-local provider hub.
It stores no provider credential or provider session and executes no entrant or
model code.  It demonstrates only account-to-runner key binding, signed
transport, durable fixture-job state, and an allow-list deterministic result
projection.
"""

from provider_hub_hosted.browser_gateway import (
    AccountRateLimiter,
    BrowserAuthenticationError,
    BrowserAuthorizationGateway,
    BrowserGatewayResponse,
    BrowserRequest,
    IdempotencyResponseKeyring,
    InMemoryAccountRateLimiter,
    RateLimitDecision,
    VerifiedBrowserPrincipal,
)
from provider_hub_hosted.handlers import HostedControlPlane
from provider_hub_hosted.store import (
    BrowserMutationRecord,
    HostedControlPlaneStore,
    HostedStoreError,
    validate_idempotency_key,
)
from provider_hub_hosted.verify import (
    IncomingSignedRequest,
    SignedRequestError,
    VerifiedRunnerRequest,
    verify_signed_request,
)

__all__ = [
    "AccountRateLimiter",
    "BrowserAuthenticationError",
    "BrowserAuthorizationGateway",
    "BrowserGatewayResponse",
    "BrowserRequest",
    "BrowserMutationRecord",
    "IdempotencyResponseKeyring",
    "HostedControlPlane",
    "HostedControlPlaneStore",
    "HostedStoreError",
    "InMemoryAccountRateLimiter",
    "IncomingSignedRequest",
    "RateLimitDecision",
    "SignedRequestError",
    "VerifiedBrowserPrincipal",
    "VerifiedRunnerRequest",
    "verify_signed_request",
    "validate_idempotency_key",
]
