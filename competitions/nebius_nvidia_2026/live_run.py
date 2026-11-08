"""One-call Nebius/NVIDIA runtime evidence for the 2026 hackathon lane.

The deterministic evaluator remains provider-neutral. This module wraps exactly
one Token Factory call with runner-observed runtime evidence without retaining
the API key or raw model response in the public receipt.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

from arena.canonical import digest
from entrants.nebius_backend import NebiusTokenFactoryBackend
from competitions.nebius_nvidia_2026.structured_patch import (
    StructuredPatchError,
    evaluate_response,
    task_document,
)

LIVE_SCHEMA = "builderwars.nebius-live-run.v1"
PROMPT_VERSION = "nebius-routing-policy-repair.prompt.v1"


def provider_prompt():
    """Return the exact bounded prompt sent to Token Factory."""
    task = json.dumps(task_document(), sort_keys=True, separators=(",", ":"))
    return (
        "Solve the following bounded policy-repair task. "
        "Return exactly one JSON object matching responseSchema. "
        "Do not use markdown, prose, code fences, or extra keys.\n"
        + task
    )


def _observed_at():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def run_live_once(*, model=None, backend=None, observed_at=None, clock_ns=None):
    """Run one provider call and return a hash-only runtime/evaluation receipt.

    Passing a backend is reserved for tests. Receipts produced through an
    injected backend explicitly withhold provider/model execution claims.
    """
    injected = backend is not None
    if model is None:
        model = (
            backend.model
            if backend is not None
            else NebiusTokenFactoryBackend.DEFAULT_MODEL
        )
    if backend is None:
        backend = NebiusTokenFactoryBackend(model=model)
    elif backend.model != model:
        raise ValueError("injected backend model must equal requested model")

    prompt = provider_prompt()
    now_ns = clock_ns or time.monotonic_ns
    started = now_ns()
    response = backend.complete(prompt)
    finished = now_ns()
    duration_ms = max(0, (finished - started) // 1_000_000)

    credential_present = bool(os.environ.get(NebiusTokenFactoryBackend.ENV_VAR))
    runtime_evidence = {
        "transport": "injected-test-double" if injected else "nebius-https",
        "providerCallObserved": not injected,
        "modelExecutionObservedByRunner": not injected,
        "independentProviderAttestation": False,
        "credentialObserved": credential_present if not injected else False,
        "credentialValueRetained": False,
        "rawResponseRetained": False,
    }

    try:
        evaluation = evaluate_response(response, model=model)
        status = evaluation["status"]
    except StructuredPatchError as error:
        evaluation = {
            "status": "invalid",
            "error": error.__class__.__name__,
        }
        status = "invalid"

    receipt = {
        "schema": LIVE_SCHEMA,
        "observedAt": observed_at or _observed_at(),
        "status": status,
        "provider": "nebius-token-factory",
        "endpoint": NebiusTokenFactoryBackend.PINNED_ENDPOINT,
        "model": model,
        "promptVersion": PROMPT_VERSION,
        "taskVersion": task_document()["taskVersion"],
        "taskDigest": digest(task_document()),
        "promptDigest": digest(prompt),
        "responseTextDigest": digest(response),
        "durationMs": duration_ms,
        "bounds": {
            "maxProviderCalls": 1,
            "maxTokens": NebiusTokenFactoryBackend.MAX_TOKENS,
            "timeoutMs": int(round(backend.timeout_s * 1000)),
        },
        "runtimeEvidence": runtime_evidence,
        "evaluation": evaluation,
    }
    receipt["receiptDigest"] = digest(receipt)
    return receipt
