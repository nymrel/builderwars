"""Deterministic structured-patch evaluation for an agentic coding workflow.

The entrant edits a small routing-policy document through a bounded JSON patch
vocabulary. The evaluator never executes entrant-authored code. It produces a
hash-only receipt suitable for replay and comparison across providers.
"""

from __future__ import annotations

import copy
import json

from arena.canonical import canonical_bytes, digest


SCHEMA = "builderwars.structured-patch-receipt.v1"
TASK_VERSION = "nebius-routing-policy-repair.v1"
PROVIDER = "nebius-token-factory"
MAX_RESPONSE_BYTES = 16 * 1024
MAX_PATCHES = 8

BASELINE_POLICY = {
    "routes": {
        "trusted-internal": {
            "runner": "trusted-studio-local",
            "execute": True,
            "network": False,
        },
        "untrusted-public": {
            "runner": "trusted-studio-local",
            "execute": True,
            "network": True,
        },
        "unclassified": {
            "runner": "trusted-studio-local",
            "execute": True,
            "network": False,
        },
    }
}

EXPECTED_POLICY = {
    "routes": {
        "trusted-internal": {
            "runner": "trusted-studio-local",
            "execute": True,
            "network": False,
        },
        "untrusted-public": {
            "runner": "disposable-isolated",
            "execute": False,
            "network": False,
        },
        "unclassified": {
            "runner": "none",
            "execute": False,
            "network": False,
        },
    }
}

_PATH_TYPES = {
    "/routes/trusted-internal/runner": str,
    "/routes/trusted-internal/execute": bool,
    "/routes/trusted-internal/network": bool,
    "/routes/untrusted-public/runner": str,
    "/routes/untrusted-public/execute": bool,
    "/routes/untrusted-public/network": bool,
    "/routes/unclassified/runner": str,
    "/routes/unclassified/execute": bool,
    "/routes/unclassified/network": bool,
}
_RUNNERS = {"trusted-studio-local", "disposable-isolated", "none"}


class StructuredPatchError(ValueError):
    """The entrant response is malformed or outside the bounded task contract."""


class _DuplicateKey(StructuredPatchError):
    pass


def _strict_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKey(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def task_document():
    """Return the exact public task presented to an entrant."""

    return {
        "taskVersion": TASK_VERSION,
        "objective": (
            "Repair the routing policy so trusted internal work stays local, "
            "untrusted public work is held for a disposable isolated runner, "
            "and unclassified work cannot execute."
        ),
        "baseline": copy.deepcopy(BASELINE_POLICY),
        "responseSchema": {
            "patches": [
                {
                    "op": "replace",
                    "path": "one allowed leaf path",
                    "value": "a runner string or boolean",
                }
            ]
        },
        "allowedPaths": sorted(_PATH_TYPES),
        "limits": {
            "maxResponseBytes": MAX_RESPONSE_BYTES,
            "maxPatches": MAX_PATCHES,
            "generatedCodeExecuted": False,
        },
    }


def _parse_response(response_text):
    if not isinstance(response_text, str):
        raise StructuredPatchError("response must be UTF-8 text")
    encoded = response_text.encode("utf-8")
    if not encoded or len(encoded) > MAX_RESPONSE_BYTES:
        raise StructuredPatchError(
            f"response must contain 1..{MAX_RESPONSE_BYTES} UTF-8 bytes"
        )
    try:
        response = json.loads(response_text, object_pairs_hook=_strict_object)
    except _DuplicateKey:
        raise
    except (json.JSONDecodeError, UnicodeError) as error:
        raise StructuredPatchError("response must be strict JSON") from error
    if not isinstance(response, dict) or set(response) != {"patches"}:
        raise StructuredPatchError("response must contain only a patches array")
    patches = response["patches"]
    if not isinstance(patches, list) or not 1 <= len(patches) <= MAX_PATCHES:
        raise StructuredPatchError(f"patches must contain 1..{MAX_PATCHES} entries")
    return response, patches


def apply_response(response_text):
    """Validate and apply the entrant response to the immutable baseline."""

    response, patches = _parse_response(response_text)
    policy = copy.deepcopy(BASELINE_POLICY)
    seen = set()
    for index, patch in enumerate(patches):
        if not isinstance(patch, dict) or set(patch) != {"op", "path", "value"}:
            raise StructuredPatchError(
                f"patch {index} must contain exactly op, path, and value"
            )
        if patch["op"] != "replace":
            raise StructuredPatchError(f"patch {index} uses unsupported operation")
        path = patch["path"]
        if path not in _PATH_TYPES:
            raise StructuredPatchError(f"patch {index} targets a forbidden path")
        if path in seen:
            raise StructuredPatchError(f"patch {index} repeats a path")
        seen.add(path)
        value = patch["value"]
        expected_type = _PATH_TYPES[path]
        if type(value) is not expected_type:
            raise StructuredPatchError(f"patch {index} has the wrong value type")
        if expected_type is str and value not in _RUNNERS:
            raise StructuredPatchError(f"patch {index} uses an unknown runner")
        _, _, route, field = path.split("/")
        policy["routes"][route][field] = value
    return response, policy


def _checks(policy):
    checks = []
    for route in sorted(EXPECTED_POLICY["routes"]):
        for field in ("runner", "execute", "network"):
            checks.append(
                {
                    "case": f"{route}.{field}",
                    "passed": (
                        policy["routes"][route][field]
                        == EXPECTED_POLICY["routes"][route][field]
                    ),
                }
            )
    return checks


def evaluate_response(response_text, *, model, provider=PROVIDER):
    """Return a replayable score receipt without retaining the raw response."""

    if provider != PROVIDER:
        raise StructuredPatchError(f"provider must equal {PROVIDER}")
    if (
        not isinstance(model, str)
        or not model.startswith("nvidia/")
        or len(model) > 200
        or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in model)
    ):
        raise StructuredPatchError("model must be one explicit nvidia/<model> id")

    response, policy = apply_response(response_text)
    checks = _checks(policy)
    passed = sum(check["passed"] for check in checks)
    receipt = {
        "schema": SCHEMA,
        "taskVersion": TASK_VERSION,
        "taskDigest": digest(task_document()),
        "provider": provider,
        "model": model,
        "responseDigest": digest(response),
        "resultPolicyDigest": digest(policy),
        "score": {"passed": passed, "total": len(checks)},
        "status": "passed" if passed == len(checks) else "failed",
        "checks": checks,
        "boundary": {
            "generatedCodeExecuted": False,
            "providerCallObserved": False,
            "credentialObserved": False,
            "rawResponseRetained": False,
        },
    }
    receipt["receiptDigest"] = digest(receipt)
    canonical_bytes(receipt)
    return receipt

