"""Versioned BuildWars customer/runner envelopes — strict, float-free.

Seven envelope kinds, each validated against an exact key set (unknown keys are
rejected, not ignored), with canonical JSON encoding shared by signing:

  buildwars.identity.v1
  buildwars.provider_link.v1
  buildwars.provider_link.v2
  buildwars.runner_pairing.v1
  buildwars.runner_capabilities.v1
  buildwars.match_job.v1
  buildwars.result_attestation.v1

Hard rules enforced here:

* every numeric value is an integer; floats and NaN/Inf spellings fail closed;
* ids are random 128-bit public identifiers (see ``ids``);
* string values never look like secrets: emails, token/key prefixes,
  ``password=...``-style assignments, and high-entropy blobs outside the two
  designated digest fields all reject;
* provider links always say ``credential_custody: "customer_only"``;
* provider-link v2 binds a closed customer-facing connection mode to the
  catalog, fixes execution at ``customer_local_runner``, and requires account,
  entitlement, billing-route, and model attestation flags to remain false;
* runner origin may be authenticated, but ``model_attested`` and
  ``execution_claims_attested`` must be exactly false — a self-report is never
  attestation;
* match jobs and results bind game/version/seed/seats/engine digest/receipt id
  and replay verdict without changing the arena/1 contract.
"""

import json
import re

from provider_hub.catalog import (
    EXECUTABLE_PROVIDER_IDS,
    PROVIDER_IDS,
    get_provider,
    model_required_for,
)
from provider_hub.ids import id_is_valid, key_id_is_valid

SCHEMA_NAMES = (
    "buildwars.identity.v1",
    "buildwars.provider_link.v1",
    "buildwars.provider_link.v2",
    "buildwars.runner_pairing.v1",
    "buildwars.runner_capabilities.v1",
    "buildwars.match_job.v1",
    "buildwars.result_attestation.v1",
)

MIN_TS = 1577836800  # 2020-01-01Z
MAX_TS = 4102444800  # 2100-01-01Z

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_CODE_RE = re.compile(r"^[A-Za-z0-9._~-]{8,512}$")

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization|bearer|cookie)"
    r"\s*[=:]\s*\S"
)
_SECRET_PREFIXES = (
    "sk-or-v1-",
    "sk-or-",
    "sk-ant-",
    "sk-proj-",
    "sk-",
    "Bearer ",
    "bearer ",
    "ghp_",
    "gho_",
    "ghu_",
    "xoxb-",
    "xoxp-",
    "xoxa-",
    "AKIA",
)
# Fields whose well-formed value is *supposed* to be a long opaque digest.
_DIGEST_FIELDS = frozenset({"engine_digest", "receipt_id"})

EXECUTION_CLAIMS = ("scripted", "model", "hybrid")
REPLAY_VERDICTS = ("PASS", "FAIL")


class SchemaError(ValueError):
    """Any envelope validation failure. Messages name the field and reason."""


# ---------------------------------------------------------------------------
# strict JSON decode / canonical encode
# ---------------------------------------------------------------------------


def _pairs_no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise SchemaError(f"duplicate JSON object key {key!r}")
        seen[key] = value
    return seen


def _reject_floats(value, path):
    if isinstance(value, float):
        raise SchemaError(f"float value at {path}; BuildWars envelopes carry integers only")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_floats(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _reject_floats(item, f"{path}[{i}]")


def decode_strict(data):
    """Parse JSON rejecting duplicate keys, floats, and non-object roots."""
    if isinstance(data, (bytes, bytearray)):
        try:
            text = bytes(data).decode("utf-8")
        except UnicodeDecodeError as error:
            raise SchemaError("payload is not valid UTF-8") from error
    elif isinstance(data, str):
        text = data
    else:
        raise SchemaError("payload must be bytes or str")
    try:
        value = json.loads(text, object_pairs_hook=_pairs_no_duplicates)
    except json.JSONDecodeError as error:
        raise SchemaError(f"invalid JSON: {error.msg} at char {error.pos}") from error
    if not isinstance(value, dict):
        raise SchemaError("top-level payload must be a JSON object")
    _reject_floats(value, "$")
    return value


def encode_canonical(payload):
    """Deterministic encoding used by both transport and HMAC signing.

    ``allow_nan=False`` makes float/NaN/Infinity spellings a hard encode error
    instead of relying on callers to pre-clean their payloads.
    """
    _reject_floats(payload, "$")
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# hostile-value scanning
# ---------------------------------------------------------------------------


def scan_for_secret_shapes(payload, allowed_digest_fields=frozenset()):
    """Reject any string that looks like a credential in a non-secret envelope."""
    allowed = _DIGEST_FIELDS | set(allowed_digest_fields)

    def walk(node, path):
        if isinstance(node, dict):
            for key, item in node.items():
                if isinstance(key, str) and _key_is_secret_shaped(key) and key not in allowed:
                    raise SchemaError(f"key {path}.{key} is a forbidden secret-bearing name")
                walk(item, f"{path}.{key}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            _value_is_clean(node, path, key_ok=path.split(".")[-1] in allowed)

    walk(payload, "$")


# Field names that legitimately contain a forbidden substring but are facts,
# not secrets — matched exactly, never as substrings.
_SAFE_KEY_NAMES = frozenset({"credential_custody"})


def _key_is_secret_shaped(key):
    if key in _SAFE_KEY_NAMES:
        return False
    lowered = key.lower()
    return (
        any(mark in lowered for mark in (
            "token", "secret", "password", "passwd", "cookie", "api_key",
            "apikey", "refresh", "verifier", "credential", "email",
            "authorization",
        ))
        or lowered == "code"
    )


def _value_is_clean(text, path, key_ok=False):
    if not text:
        return
    if _EMAIL_RE.search(text):
        raise SchemaError(f"{path}: email-shaped values never enter BuildWars envelopes")
    for prefix in _SECRET_PREFIXES:
        if text.startswith(prefix):
            raise SchemaError(f"{path}: value carries credential prefix {prefix.strip()!r}")
    if _ASSIGNMENT_RE.search(text):
        raise SchemaError(f"{path}: value embeds a credential assignment")
    if key_ok:
        return
    if len(text) >= 40 and re.fullmatch(r"[A-Za-z0-9._~-]+", text):
        raise SchemaError(
            f"{path}: high-entropy opaque blob outside designated digest fields"
        )


# ---------------------------------------------------------------------------
# small typed getters
# ---------------------------------------------------------------------------


def _exact_keys(payload, expected, schema):
    got = set(payload)
    want = set(expected)
    unknown = sorted(got - want)
    missing = sorted(want - got)
    if unknown:
        raise SchemaError(f"{schema}: unknown keys {unknown}")
    if missing:
        raise SchemaError(f"{schema}: missing keys {missing}")


def _require(schema, field, value, check, expected_type=None):
    if expected_type is not None and not isinstance(value, expected_type):
        raise SchemaError(
            f"{schema}.{field}: expected {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )
    try:
        ok = check(value)
    except SchemaError:
        raise
    except Exception as error:
        raise SchemaError(f"{schema}.{field}: rejected ({error.__class__.__name__})") from None
    if ok is False:
        raise SchemaError(f"{schema}.{field}: rejected value {value!r}")
    return value


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _int_field(schema, field, value, minimum=None, maximum=None):
    def check(v):
        if not _is_int(v):
            return False
        if minimum is not None and v < minimum:
            return False
        if maximum is not None and v > maximum:
            return False
        return True

    return _require(schema, field, value, check, int)


def _ts_field(schema, field, value):
    return _int_field(schema, field, value, MIN_TS, MAX_TS)


def _str_field(schema, field, value, max_len, allow_empty=False):
    def check(v):
        if not isinstance(v, str):
            return False
        if not v and not allow_empty:
            return False
        if len(v) > max_len:
            return False
        return not any(ord(ch) < 32 or ord(ch) == 127 for ch in v)

    return _require(schema, field, value, check, str)


def _bool_field(schema, field, value):
    return _require(schema, field, value, lambda v: isinstance(v, bool), bool)


def _id_field(schema, field, value, kind):
    return _require(schema, field, value, lambda v: id_is_valid(kind, v), str)


def _digest_field(schema, field, value):
    return _require(schema, field, value, lambda v: bool(_DIGEST_RE.fullmatch(v)), str)


def _slug_field(schema, field, value):
    return _require(schema, field, value, lambda v: bool(_SLUG_RE.fullmatch(v)), str)


def _sorted_unique(values):
    return list(values) == sorted(set(values))


def _seats_field(schema, value):
    _require(schema, "seats", value, lambda v: isinstance(v, dict), dict)
    _exact_keys(value, {"count", "your_seat"}, f"{schema}.seats")
    count = _int_field(schema, "seats.count", value["count"], 2, 16)
    your_seat = _int_field(schema, "seats.your_seat", value["your_seat"], 0, count - 1)
    return {"count": count, "your_seat": your_seat}


# ---------------------------------------------------------------------------
# per-envelope validators (each returns a normalized dict)
# ---------------------------------------------------------------------------


def validate_identity(payload):
    s = "buildwars.identity.v1"
    _require(s, "schema", payload.get("schema"), lambda v: v == s, str)
    _exact_keys(
        payload,
        {"schema", "identity_id", "display_name", "created_at"},
        s,
    )
    out = {
        "schema": s,
        "identity_id": _id_field(
            s, "identity_id", payload["identity_id"], "identity"
        ),
        "display_name": _str_field(s, "display_name", payload["display_name"], 80),
        "created_at": _ts_field(s, "created_at", payload["created_at"]),
    }
    scan_for_secret_shapes(out)
    return out


def validate_provider_link(payload):
    s = "buildwars.provider_link.v1"
    _require(s, "schema", payload.get("schema"), lambda v: v == s, str)
    _exact_keys(
        payload,
        {
            "schema", "link_id", "identity_id", "provider", "connection_transport",
            "credential_custody", "model_required", "model_declared", "created_at",
        },
        s,
    )
    provider = _require(
        s, "provider", payload["provider"], lambda v: v in PROVIDER_IDS, str
    )
    entry = get_provider(provider)
    if entry["local_execution"] is not True:
        raise SchemaError(f"{s}.provider: execution is currently unsupported")
    custody = _require(
        s,
        "credential_custody",
        payload["credential_custody"],
        lambda v: v == "customer_only",
        str,
    )
    model_required = _bool_field(s, "model_required", payload["model_required"])
    if model_required != entry["model_required"]:
        raise SchemaError(
            f"{s}.model_required: contradicts catalog for {provider!r}"
        )
    declared = payload["model_declared"]
    if declared is not None:
        declared = _require(
            s,
            "model_declared",
            declared,
            lambda v: isinstance(v, str)
            and 0 < len(v) <= 120
            and not any(ch.isspace() for ch in v)
            and not v.startswith("-"),
            str,
        )
    if entry["model_required"] and declared is None:
        raise SchemaError(f"{s}.model_declared: required for provider {provider!r}")
    transport = _require(
        s,
        "connection_transport",
        payload["connection_transport"],
        lambda v: v == entry["connection_transport"],
        str,
    )
    out = {
        "schema": s,
        "link_id": _id_field(s, "link_id", payload["link_id"], "provider_link"),
        "identity_id": _id_field(s, "identity_id", payload["identity_id"], "identity"),
        "provider": provider,
        "connection_transport": transport,
        "credential_custody": custody,
        "model_required": model_required,
        "model_declared": declared,
        "created_at": _ts_field(s, "created_at", payload["created_at"]),
    }
    scan_for_secret_shapes(out)
    return out


def validate_provider_link_v2(payload):
    """Validate the additive provider-link v2 truth contract.

    v1 remains accepted byte-for-byte. v2 does not infer connection semantics
    from a subprocess transport: it binds the selected customer-facing mode to
    the six-provider catalog and makes every unavailable attestation explicit.
    A future hosted OAuth/account proof or independent execution attestation
    requires a new schema rather than weakening these exact-false invariants.
    """
    s = "buildwars.provider_link.v2"
    _require(s, "schema", payload.get("schema"), lambda v: v == s, str)
    _exact_keys(
        payload,
        {
            "schema", "link_id", "identity_id", "provider", "connection_mode",
            "connection_transport", "execution_boundary", "credential_custody",
            "model_required", "model_declared", "provider_account_attested",
            "plan_entitlement_attested", "billing_route_attested",
            "model_attested", "created_at",
        },
        s,
    )
    provider = _require(
        s, "provider", payload["provider"], lambda v: v in PROVIDER_IDS, str
    )
    entry = get_provider(provider)
    if entry["local_execution"] is not True:
        raise SchemaError(f"{s}.provider: execution is currently unsupported")
    connection_mode = _require(
        s,
        "connection_mode",
        payload["connection_mode"],
        lambda v: v == entry["connection_mode"],
        str,
    )
    transport = _require(
        s,
        "connection_transport",
        payload["connection_transport"],
        lambda v: v == entry["connection_transport"],
        str,
    )
    execution_boundary = _require(
        s,
        "execution_boundary",
        payload["execution_boundary"],
        lambda v: v == "customer_local_runner",
        str,
    )
    custody = _require(
        s,
        "credential_custody",
        payload["credential_custody"],
        lambda v: v == "customer_only",
        str,
    )
    model_required = _bool_field(s, "model_required", payload["model_required"])
    if model_required != entry["model_required"]:
        raise SchemaError(
            f"{s}.model_required: contradicts catalog for {provider!r}"
        )
    declared = payload["model_declared"]
    if declared is not None:
        declared = _require(
            s,
            "model_declared",
            declared,
            lambda v: isinstance(v, str)
            and 0 < len(v) <= 120
            and not any(ch.isspace() for ch in v)
            and not v.startswith("-"),
            str,
        )
    if entry["model_required"] and declared is None:
        raise SchemaError(f"{s}.model_declared: required for provider {provider!r}")

    unattested = {}
    for field in (
        "provider_account_attested",
        "plan_entitlement_attested",
        "billing_route_attested",
        "model_attested",
    ):
        value = _bool_field(s, field, payload[field])
        if value is not False:
            raise SchemaError(f"{s}.{field}: must be exactly false")
        unattested[field] = value

    out = {
        "schema": s,
        "link_id": _id_field(s, "link_id", payload["link_id"], "provider_link"),
        "identity_id": _id_field(s, "identity_id", payload["identity_id"], "identity"),
        "provider": provider,
        "connection_mode": connection_mode,
        "connection_transport": transport,
        "execution_boundary": execution_boundary,
        "credential_custody": custody,
        "model_required": model_required,
        "model_declared": declared,
        **unattested,
        "created_at": _ts_field(s, "created_at", payload["created_at"]),
    }
    scan_for_secret_shapes(out)
    return out


def validate_runner_pairing(payload):
    s = "buildwars.runner_pairing.v1"
    _require(s, "schema", payload.get("schema"), lambda v: v == s, str)
    _exact_keys(
        payload,
        {
            "schema", "pairing_id", "identity_id", "runner_id", "key_id",
            "origin_authenticated", "created_at", "signed_at",
        },
        s,
    )
    out = {
        "schema": s,
        "pairing_id": _id_field(s, "pairing_id", payload["pairing_id"], "runner_pairing"),
        "identity_id": _id_field(s, "identity_id", payload["identity_id"], "identity"),
        "runner_id": _id_field(s, "runner_id", payload["runner_id"], "runner"),
        "key_id": _require(
            s, "key_id", payload["key_id"], key_id_is_valid, str
        ),
        "origin_authenticated": _bool_field(
            s, "origin_authenticated", payload["origin_authenticated"]
        ),
        "created_at": _ts_field(s, "created_at", payload["created_at"]),
        "signed_at": _ts_field(s, "signed_at", payload["signed_at"]),
    }
    scan_for_secret_shapes(out)
    return out


def validate_runner_capabilities(payload):
    s = "buildwars.runner_capabilities.v1"
    _require(s, "schema", payload.get("schema"), lambda v: v == s, str)
    _exact_keys(
        payload,
        {
            "schema", "runner_id", "providers", "games", "protocol",
            "declared_execution_claim", "model_attested",
            "execution_claims_attested", "created_at", "signed_at",
        },
        s,
    )
    providers = payload["providers"]
    _require(s, "providers", providers, lambda v: isinstance(v, list) and bool(v), list)
    for item in providers:
        _require(
            s,
            "providers[]",
            item,
            lambda x: x in EXECUTABLE_PROVIDER_IDS,
            str,
        )
    if not _sorted_unique(providers):
        raise SchemaError(f"{s}.providers: must be sorted and unique")
    games = payload["games"]
    _require(s, "games", games, lambda v: isinstance(v, list) and bool(v), list)
    games = [_slug_field(s, "games[]", item) for item in games]
    if len(games) > 12 or not _sorted_unique(games):
        raise SchemaError(f"{s}.games: must be <=12, sorted, unique slugs")
    claim = _require(
        s,
        "declared_execution_claim",
        payload["declared_execution_claim"],
        lambda v: v in EXECUTION_CLAIMS,
        str,
    )
    model_attested = payload["model_attested"]
    claims_attested = payload["execution_claims_attested"]
    if model_attested is not False:
        raise SchemaError(f"{s}.model_attested: must be exactly false; self-reports are not attestation")
    if claims_attested is not False:
        raise SchemaError(
            f"{s}.execution_claims_attested: must be exactly false; self-reports are not attestation"
        )
    protocol = _require(
        s, "protocol", payload["protocol"], lambda v: v == "arena/1", str
    )
    out = {
        "schema": s,
        "runner_id": _id_field(s, "runner_id", payload["runner_id"], "runner"),
        "providers": list(providers),
        "games": games,
        "protocol": protocol,
        "declared_execution_claim": claim,
        "model_attested": False,
        "execution_claims_attested": False,
        "created_at": _ts_field(s, "created_at", payload["created_at"]),
        "signed_at": _ts_field(s, "signed_at", payload["signed_at"]),
    }
    scan_for_secret_shapes(out)
    return out


def validate_match_job(payload):
    s = "buildwars.match_job.v1"
    _require(s, "schema", payload.get("schema"), lambda v: v == s, str)
    _exact_keys(
        payload,
        {
            "schema", "job_id", "identity_id", "runner_id", "game", "game_version",
            "seed", "seats", "engine_digest", "created_at", "expires_at",
        },
        s,
    )
    created_at = _ts_field(s, "created_at", payload["created_at"])
    expires_at = _ts_field(s, "expires_at", payload["expires_at"])
    if expires_at <= created_at:
        raise SchemaError(f"{s}.expires_at: must be after created_at")
    seed = payload["seed"]
    if not _is_int(seed) or not 0 <= seed < 2**63:
        raise SchemaError(f"{s}.seed: must be an integer in [0, 2^63)")
    out = {
        "schema": s,
        "job_id": _id_field(s, "job_id", payload["job_id"], "match_job"),
        "identity_id": _id_field(s, "identity_id", payload["identity_id"], "identity"),
        "runner_id": _id_field(s, "runner_id", payload["runner_id"], "runner"),
        "game": _slug_field(s, "game", payload["game"]),
        "game_version": _require(
            s, "game_version", payload["game_version"],
            lambda v: bool(_VERSION_RE.fullmatch(v)), str,
        ),
        "seed": seed,
        "seats": _seats_field(s, payload["seats"]),
        "engine_digest": _digest_field(s, "engine_digest", payload["engine_digest"]),
        "created_at": created_at,
        "expires_at": expires_at,
    }
    scan_for_secret_shapes(out)
    return out


def validate_result_attestation(payload):
    s = "buildwars.result_attestation.v1"
    _require(s, "schema", payload.get("schema"), lambda v: v == s, str)
    _exact_keys(
        payload,
        {
            "schema", "attestation_id", "job_id", "identity_id", "runner_id",
            "receipt_id", "replay_verdict", "engine_digest", "game",
            "game_version", "seed", "seats", "source_counts", "model_attested",
            "execution_claims_attested", "signed_at",
        },
        s,
    )
    verdict = _require(
        s, "replay_verdict", payload["replay_verdict"],
        lambda v: v in REPLAY_VERDICTS, str,
    )
    counts = payload["source_counts"]
    _require(s, "source_counts", counts, lambda v: isinstance(v, dict), dict)
    _exact_keys(counts, {"model", "fallback"}, f"{s}.source_counts")
    counts_out = {
        "model": _int_field(s, "source_counts.model", counts["model"], 0),
        "fallback": _int_field(s, "source_counts.fallback", counts["fallback"], 0),
    }
    if payload["model_attested"] is not False or payload["execution_claims_attested"] is not False:
        raise SchemaError(
            f"{s}: model_attested and execution_claims_attested must be exactly false"
        )
    out = {
        "schema": s,
        "attestation_id": _id_field(
            s, "attestation_id", payload["attestation_id"], "result_attestation"
        ),
        "job_id": _id_field(s, "job_id", payload["job_id"], "match_job"),
        "identity_id": _id_field(s, "identity_id", payload["identity_id"], "identity"),
        "runner_id": _id_field(s, "runner_id", payload["runner_id"], "runner"),
        "receipt_id": _digest_field(s, "receipt_id", payload["receipt_id"]),
        "replay_verdict": verdict,
        "engine_digest": _digest_field(s, "engine_digest", payload["engine_digest"]),
        "game": _slug_field(s, "game", payload["game"]),
        "game_version": _require(
            s, "game_version", payload["game_version"],
            lambda v: bool(_VERSION_RE.fullmatch(v)), str,
        ),
        "seed": payload["seed"],
        "seats": _seats_field(s, payload["seats"]),
        "source_counts": counts_out,
        "model_attested": False,
        "execution_claims_attested": False,
        "signed_at": _ts_field(s, "signed_at", payload["signed_at"]),
    }
    if not _is_int(out["seed"]) or not 0 <= out["seed"] < 2**63:
        raise SchemaError(f"{s}.seed: must be an integer in [0, 2^63)")
    scan_for_secret_shapes(out)
    return out


_VALIDATORS = {
    "buildwars.identity.v1": validate_identity,
    "buildwars.provider_link.v1": validate_provider_link,
    "buildwars.provider_link.v2": validate_provider_link_v2,
    "buildwars.runner_pairing.v1": validate_runner_pairing,
    "buildwars.runner_capabilities.v1": validate_runner_capabilities,
    "buildwars.match_job.v1": validate_match_job,
    "buildwars.result_attestation.v1": validate_result_attestation,
}


def validate_envelope(payload):
    """Dispatch on the schema discriminator; unknown schemas fail closed."""
    if not isinstance(payload, dict):
        raise SchemaError("envelope must be a dict")
    schema = payload.get("schema")
    validator = _VALIDATORS.get(schema)
    if validator is None:
        raise SchemaError(f"unknown schema {schema!r}; supported: {', '.join(SCHEMA_NAMES)}")
    return validator(payload)


def bind_result_to_job(result, job):
    """Cross-check that a result attests exactly the job it answers.

    Both payloads must already have passed their own validators. Returns the
    result on success; any mismatch of the bound fields raises.
    """
    bound_fields = ("game", "game_version", "seed", "seats", "engine_digest")
    for field in bound_fields:
        if result[field] != job[field]:
            raise SchemaError(
                f"result.job binding mismatch on {field}: "
                f"{result[field]!r} != {job[field]!r}"
            )
    for field in ("job_id", "runner_id", "identity_id"):
        if result[field] != job[field]:
            raise SchemaError(
                f"result.{field} does not reference this job's {field}"
            )
    return result
