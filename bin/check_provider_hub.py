#!/usr/bin/env python3
"""Adversarial contracts for the BuildWars customer provider hub.

Ten sections, per release packet:
  1. exact six-provider catalog and connection plans
  2. strict schema / unknown-key / type / no-float / public-id checks
  3. secret-field and secret-shaped-value rejection
  4. HMAC pairing sign/verify/tamper/stale/wrong-user/wrong-runner
  5. OpenRouter PKCE S256 deterministic vector + hostile cases (injected transport)
  6. provider adapter argv/env/label contracts (mocked subprocess/network ONLY)
  7. both harnesses accept provider selection; fallback/source-count truth preserved
  8. generated arena manifests carry env NAMES only, never values
  9. grep/import guard: arena/** has no provider hub, HTTP, socket, token,
     OAuth, or credential dependency
 10. the existing regression ladder stays green

Every attack below is asserted to FAIL CLOSED — a silent acceptance is a bug.
"""

import argparse
import ast
import copy
import io
import json
import os
import operator
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from provider_hub import pkce as pkce_mod  # noqa: E402
from provider_hub.catalog import (  # noqa: E402
    PROVIDER_IDS,
    ProviderError,
    backend_kind_for,
    connect_plan,
    get_provider,
    model_required_for,
    public_catalog,
    transport_for,
)
from provider_hub.ids import KEY_ID_RE, id_is_valid, new_id
from provider_hub.schemas import (  # noqa: E402
    SCHEMA_NAMES,
    SchemaError,
    bind_result_to_job,
    decode_strict,
    encode_canonical,
    validate_envelope,
)
from provider_hub.secrets import SecretValue, redact
from provider_hub.signing import (  # noqa: E402
    InMemoryReplayGuard,
    PairingKey,
    SigningError,
    generate_pairing_key,
    sign_payload,
    verify_signature,
)

NOW = int(time.time())
RFC_VECTOR_VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
RFC_VECTOR_CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def expect_error(fn, exc, fragment=None):
    try:
        fn()
    except exc as error:
        if fragment is not None:
            require(fragment in str(error), f"expected {fragment!r} in {error!r}")
        return error
    raise AssertionError(f"expected {exc.__name__}")


def banner(text):
    print(f"[section {text}]")


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def identity_payload(**overrides):
    payload = {
        "schema": "buildwars.identity.v1",
        "identity_id": new_id("identity"),
        "display_name": "Jalen",
        "created_at": NOW - 60,
    }
    payload.update(overrides)
    return payload


def link_payload(**overrides):
    payload = {
        "schema": "buildwars.provider_link.v1",
        "link_id": new_id("provider_link"),
        "identity_id": new_id("identity"),
        "provider": "opencode",
        "connection_transport": "local_cli_subprocess",
        "credential_custody": "customer_only",
        "model_required": True,
        "model_declared": "anthropic/claude-sonnet-5",
        "created_at": NOW - 60,
    }
    payload.update(overrides)
    return payload


def pairing_payload(key, **overrides):
    payload = {
        "schema": "buildwars.runner_pairing.v1",
        "pairing_id": new_id("runner_pairing"),
        "identity_id": new_id("identity"),
        "runner_id": new_id("runner"),
        "key_id": key.key_id,
        "origin_authenticated": True,
        "created_at": NOW - 60,
        "signed_at": NOW,
    }
    payload.update(overrides)
    return payload


def capabilities_payload(**overrides):
    payload = {
        "schema": "buildwars.runner_capabilities.v1",
        "runner_id": new_id("runner"),
        "providers": ["chatgpt_codex", "openrouter"],
        "games": ["fantasy_redraft", "ten_fronts"],
        "protocol": "arena/1",
        "declared_execution_claim": "model",
        "model_attested": False,
        "execution_claims_attested": False,
        "created_at": NOW - 60,
        "signed_at": NOW,
    }
    payload.update(overrides)
    return payload


def job_payload(**overrides):
    payload = {
        "schema": "buildwars.match_job.v1",
        "job_id": new_id("match_job"),
        "identity_id": new_id("identity"),
        "runner_id": new_id("runner"),
        "game": "fantasy_redraft",
        "game_version": "v1",
        "seed": 9200,
        "seats": {"count": 2, "your_seat": 0},
        "engine_digest": "ab" * 32,
        "created_at": NOW - 60,
        "expires_at": NOW + 3600,
    }
    payload.update(overrides)
    return payload


def result_payload(job=None, **overrides):
    payload = {
        "schema": "buildwars.result_attestation.v1",
        "attestation_id": new_id("result_attestation"),
        "job_id": job["job_id"] if job else new_id("match_job"),
        "identity_id": job["identity_id"] if job else new_id("identity"),
        "runner_id": job["runner_id"] if job else new_id("runner"),
        "receipt_id": "cd" * 32,
        "replay_verdict": "PASS",
        "engine_digest": job["engine_digest"] if job else "ab" * 32,
        "game": job["game"] if job else "fantasy_redraft",
        "game_version": job["game_version"] if job else "v1",
        "seed": job["seed"] if job else 9200,
        "seats": copy.deepcopy(job["seats"]) if job else {"count": 2, "your_seat": 0},
        "source_counts": {"model": 12, "fallback": 4},
        "model_attested": False,
        "execution_claims_attested": False,
        "signed_at": NOW,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# 1. catalog
# ---------------------------------------------------------------------------


def check_catalog():
    banner("1 catalog")
    require(PROVIDER_IDS == (
        "chatgpt_codex", "claude_code", "opencode", "openrouter", "hermes",
        "custom_agent",
    ), "catalog must be exactly the six contracted providers")
    listing = public_catalog()
    require([pid for pid, _ in listing] == list(PROVIDER_IDS), "canonical order")

    fact_keys = {
        "display_name", "connection_transport", "auth_plan", "status_plan",
        "credential_custody", "model_required", "backend_kind", "limitations",
    }
    allowed_transports = {
        "local_cli_subprocess", "local_cli_auth_delegation",
        "local_pkce_http_exchange", "customer_command_stdio",
    }
    for pid, entry in listing:
        require(set(entry) >= fact_keys, f"{pid}: missing fact keys")
        require(entry["credential_custody"] == "customer_only", f"{pid}: custody")
        require(entry["connection_transport"] in allowed_transports, f"{pid}: transport")
        require(len(entry["auth_plan"]) >= 2, f"{pid}: plan must have real steps")
        require(len(entry["status_plan"]) > 10, f"{pid}: status guidance required")
        require(isinstance(entry["model_required"], bool), f"{pid}: model_required")
        require(len(entry["limitations"]) >= 1, f"{pid}: limitations declared")

    # catalog facts agree across accessors
    require(transport_for("openrouter") == "local_pkce_http_exchange", "pkce transport")
    require(model_required_for("hermes") is True, "hermes needs a model")
    require(backend_kind_for("custom_agent") == "custom_cli", "custom kind")

    # immutability is REAL, not an incomplete dict subclass
    entry = get_provider("openrouter")
    expect_error(lambda: operator.setitem(entry, "display_name", "x"), TypeError)
    try:
        entry |= {"display_name": "x"}
        raise AssertionError("|= must not mutate a frozen catalog entry")
    except TypeError:
        pass
    expect_error(lambda: entry.setdefault("new_key", 1), AttributeError)
    expect_error(lambda: entry["auth_plan"].append("x"), AttributeError)
    for pid, frozen in listing:
        require(not hasattr(frozen, "setdefault"), f"{pid}: setdefault must not exist")
        require(type(frozen).__name__ == "mappingproxy", f"{pid}: frozen mapping")
        require(isinstance(frozen["auth_plan"], tuple), f"{pid}: plan is a tuple")

    # truthful scope: no blanket legal overclaims anywhere in the catalog
    catalog_src = open(
        os.path.join(ROOT, "provider_hub", "catalog.py"), encoding="utf-8"
    ).read()
    for overclaim in ("prohibited in writing", "only lane", "never leaves the runner"):
        require(overclaim not in catalog_src, f"catalog must not claim {overclaim!r}")
    custom = get_provider("custom_agent")
    custom_text = " ".join(custom["limitations"]) + " " + " ".join(custom["auth_plan"])
    require("NOT an arena/1" in custom_text,
            "custom_agent must distinguish prompt/stdout from arena/1 JSONL")
    require(custom["connection_transport"] == "customer_command_stdio",
            "custom_agent transport names its actual prompt/stdout contract")
    require("JSON argv" in " ".join(custom["auth_plan"]),
            "custom_agent declares an explicit repeatable JSON argv vector")

    plan = connect_plan("chatgpt_codex")
    require("customer_only" in plan["custody"], "plan names custody")
    require(all(step[0].isdigit() for step in plan["steps"]), "numbered steps")
    expect_error(lambda: get_provider("gemini_pro"), ProviderError)
    expect_error(lambda: connect_plan(""), ProviderError)
    expect_error(lambda: get_provider(None), ProviderError)
    print("[PASS] six immutable providers, facts-only plans, fail-closed lookups")


# ---------------------------------------------------------------------------
# 2. schemas
# ---------------------------------------------------------------------------


def check_schemas():
    banner("2 schemas")
    require(SCHEMA_NAMES == (
        "buildwars.identity.v1", "buildwars.provider_link.v1",
        "buildwars.runner_pairing.v1", "buildwars.runner_capabilities.v1",
        "buildwars.match_job.v1", "buildwars.result_attestation.v1",
    ), "exact six envelopes")
    for name in SCHEMA_NAMES:
        require(name.startswith("buildwars.") and name.endswith(".v1"), name)

    # every envelope validates and roundtrips canonically
    samples = [
        identity_payload(),
        link_payload(),
        pairing_payload(generate_pairing_key()),
        capabilities_payload(),
        job_payload(),
        result_payload(),
    ]
    for sample in samples:
        validated = validate_envelope(sample)
        canonical = encode_canonical(validated)
        require(decode_strict(canonical) is not None, "strict decode accepts own encoding")
        require(
            encode_canonical(decode_strict(canonical)) == canonical,
            "canonical encoding is stable",
        )
    result_payload(samples[4])  # binds cleanly against its job fixture

    def reject(mutate, fragment):
        for factory in (
            lambda: identity_payload(),
            lambda: link_payload(),
            lambda: capabilities_payload(),
            lambda: job_payload(),
            lambda: result_payload(),
        ):
            payload = factory()
            probe = copy.deepcopy(payload)
            try:
                mutate(probe)
            except KeyError:
                continue  # mutation targets a field this envelope lacks
            if probe == payload:
                continue  # mutation did not apply to this envelope shape
            if payload.get("schema") == "buildwars.provider_link.v1":
                continue  # link-specific mutations handled by its own validator set
            error = expect_error(lambda p=probe: validate_envelope(p), SchemaError)
            if fragment is not None:
                require(fragment in str(error), f"{fragment!r} vs {error!r}")

    # unknown keys
    reject(lambda p: p.update({"debug_flag": True}), "unknown keys")
    # missing keys
    reject(lambda p: p.pop("created_at"), "missing keys")
    # floats rejected wherever an integer timestamp lives
    reject(lambda p: p.update({"created_at": float(NOW)}) if "created_at" in p else None,
           "float")
    expect_error(lambda: validate_envelope(job_payload(seed=1.5)), SchemaError)
    expect_error(lambda: encode_canonical({"x": 1.5}), SchemaError, "float")
    expect_error(lambda: encode_canonical({"x": float("nan")}), SchemaError, "float")
    expect_error(lambda: encode_canonical({"x": float("inf")}), SchemaError, "float")
    # bool masquerading as int
    expect_error(lambda: validate_envelope(identity_payload(created_at=True)), SchemaError)
    expect_error(lambda: validate_envelope(job_payload(seed=False)), SchemaError)
    # bad ids
    expect_error(lambda: validate_envelope(identity_payload(identity_id="bwid_short")), SchemaError)
    expect_error(lambda: validate_envelope(identity_payload(identity_id="user_42")), SchemaError)
    sequential = identity_payload(identity_id="bwid_" + "A" * 22)
    require(id_is_valid("identity", sequential["identity_id"]), "charset legal")
    # timestamps out of range
    expect_error(lambda: validate_envelope(identity_payload(created_at=42)), SchemaError)
    expect_error(lambda: validate_envelope(identity_payload(created_at=10**12)), SchemaError)

    # provider_link specifics
    expect_error(lambda: validate_envelope(link_payload(provider="not_real")), SchemaError)
    expect_error(lambda: validate_envelope(link_payload(provider="claude_code")),
                 SchemaError, "contradicts")  # transport/model facts disagree
    expect_error(lambda: validate_envelope(
        link_payload(credential_custody="platform_escrow")), SchemaError, "custody")
    expect_error(lambda: validate_envelope(
        link_payload(provider="opencode", model_required=False)), SchemaError, "contradicts")
    expect_error(lambda: validate_envelope(
        link_payload(provider="opencode", model_declared=None)), SchemaError, "required")
    expect_error(lambda: validate_envelope(
        link_payload(connection_transport="carrier_pigeon")), SchemaError, "transport")
    # provider_link unknown keys reject too
    expect_error(lambda: validate_envelope(link_payload(debug_flag=True)),
                 SchemaError, "unknown keys")
    expect_error(lambda: validate_envelope(link_payload(model_declared=3)), SchemaError)
    require(validate_envelope(link_payload())["credential_custody"] == "customer_only",
            "links always customer-custodied")

    # capabilities specifics
    expect_error(lambda: validate_envelope(capabilities_payload(model_attested=True)),
                 SchemaError, "exactly false")
    expect_error(lambda: validate_envelope(capabilities_payload(execution_claims_attested=True)),
                 SchemaError, "exactly false")
    expect_error(lambda: validate_envelope(capabilities_payload(providers=[])), SchemaError)
    expect_error(lambda: validate_envelope(capabilities_payload(providers=["nope"])), SchemaError)
    expect_error(lambda: validate_envelope(
        capabilities_payload(providers=["openrouter", "chatgpt_codex"])), SchemaError, "sorted")
    expect_error(lambda: validate_envelope(capabilities_payload(protocol="arena/2")),
                 SchemaError, "protocol")
    expect_error(lambda: validate_envelope(
        capabilities_payload(declared_execution_claim="probably-a-model")), SchemaError)

    # match_job specifics
    expect_error(lambda: validate_envelope(
        job_payload(expires_at=NOW - 120)), SchemaError, "expires_at")
    expect_error(lambda: validate_envelope(job_payload(seed=-1)), SchemaError, "seed")
    expect_error(lambda: validate_envelope(job_payload(engine_digest="AB" * 32)),
                 SchemaError, "engine_digest")
    expect_error(lambda: validate_envelope(
        job_payload(seats={"count": 2, "your_seat": 2})), SchemaError, "your_seat")
    expect_error(lambda: validate_envelope(
        job_payload(seats={"count": 17, "your_seat": 0})), SchemaError)

    # result specifics + job binding
    job = validate_envelope(job_payload())
    good = validate_envelope(result_payload(job))
    require(bind_result_to_job(good, job) is good, "binding succeeds on matching pair")
    for field, mutation in (
        ("seed", 777),
        ("game", "ten_fronts"),
        ("engine_digest", "ee" * 32),
        ("job_id", new_id("match_job")),
        ("runner_id", new_id("runner")),
    ):
        mutated = dict(good)
        mutated[field] = mutation
        expect_error(lambda m=mutated: bind_result_to_job(m, job), SchemaError, field)
    expect_error(lambda: validate_envelope(result_payload(replay_verdict="pass")),
                 SchemaError, "replay_verdict")
    expect_error(lambda: validate_envelope(
        result_payload(source_counts={"model": 1, "fallback": -1})), SchemaError)
    expect_error(lambda: validate_envelope(
        result_payload(model_attested=True)), SchemaError)

    # decode_strict: duplicate keys and non-object roots
    expect_error(lambda: decode_strict(b'{"a":1,"a":2}'), SchemaError, "duplicate")
    expect_error(lambda: decode_strict(b'[1,2]'), SchemaError, "object")
    expect_error(lambda: decode_strict(b'{"a":NaN}'), SchemaError, "float")
    expect_error(lambda: decode_strict(b'{"a":01}'), SchemaError)
    print("[PASS] strict envelopes: unknown keys, types, floats, ids, bindings")


# ---------------------------------------------------------------------------
# 3. secrets
# ---------------------------------------------------------------------------


def check_secrets():
    banner("3 secrets")
    secret_text = "sk-or-v1-EXAMPLE-" + "x" * 30
    s = SecretValue(secret_text)
    require(repr(s) == f"SecretValue(<redacted:{len(secret_text.encode())} bytes>)", repr(s))
    require(str(s) == repr(s), "str hides too")
    require(f"{s}" == repr(s), "format hides too")
    require(secret_text not in repr([s]), "list repr uses element repr")
    expect_error(lambda: json.dumps({"k": s}), TypeError)
    try:
        import pickle

        pickle.dumps(s)
        raise AssertionError("pickle must refuse SecretValue")
    except TypeError:
        pass
    expect_error(lambda: SecretValue(""), ValueError)
    expect_error(lambda: SecretValue(123), TypeError)
    require(s.reveal() == secret_text, "reveal is explicit")
    require(SecretValue(b"bytes").byte_length == 5, "bytes length")

    scrubbed = redact(f"failed auth for {secret_text} sorry", s)
    require(secret_text not in scrubbed and "[redacted]" in scrubbed, "redact works")

    # secret-SHAPED values inside ordinary envelope fields reject
    hostile_strings = [
        "contact me at jalen@example.com please",
        "sk-" + "or-v1-EXAMPLE-abc123abc123abc123abc",
        "Bearer abcdef",
        "ghp_" + "a" * 36,
        "AKIA" + "IOSFODNN7EXAMPLE",
        "password=hunter2",
        "API_KEY: abc123",
        "my token: eyJhbGciOiJIUzI1NiJ9",
        "A1" * 25,  # 50 chars of opaque blob outside designated digest fields
    ]
    for text in hostile_strings:
        expect_error(
            lambda t=text: validate_envelope(identity_payload(display_name=t)),
            SchemaError, None,
        )
    # digest-designated fields accept exactly 64 lowercase hex
    require(validate_envelope(job_payload())["engine_digest"] == "ab" * 32, "digest ok")
    expect_error(lambda: validate_envelope(
        identity_payload(identity_id="bwid_" + "9" * 21 + "/")), SchemaError)
    print("[PASS] SecretValue refuses repr/str/JSON/pickle; hostile shapes reject")


# ---------------------------------------------------------------------------
# 4. signing
# ---------------------------------------------------------------------------


def check_signing():
    banner("4 signing")
    key = generate_pairing_key()
    require(KEY_ID_RE.fullmatch(key.key_id) is not None, "key id fingerprint format")
    second = PairingKey(key.secret.reveal())
    require(second.key_id == key.key_id, "fingerprint derives deterministically")
    fresh = generate_pairing_key()
    require(fresh.key_id != key.key_id, "fresh keys differ")

    payload = pairing_payload(key)
    payload.pop("signed_at")
    signed = sign_payload(payload, key)
    require(set(signed["signature"]) == {"kind", "key_id", "value"}, "sig block shape")
    require(signed["signature"]["kind"] == "buildwars.runner_pairing.v1", "kind bound")

    lookup_ok = lambda kid: key if kid == key.key_id else None
    verified = verify_signature(signed, lookup_ok, now=NOW)
    require(verified["pairing_id"] == payload["pairing_id"], "verify returns body")
    validate_envelope(verified)
    # deterministic signature bytes
    again = sign_payload(payload, key, signed_at=signed["signed_at"])
    require(again["signature"]["value"] == signed["signature"]["value"], "deterministic MAC")

    # tamper: flip every interesting field one at a time
    for field, value in (
        ("origin_authenticated", False),
        ("identity_id", new_id("identity")),
        ("runner_id", new_id("runner")),
        ("key_id", "bpk_" + "0" * 32),
        ("pairing_id", new_id("runner_pairing")),
        ("created_at", NOW - 61),
    ):
        tampered = dict(signed)
        tampered[field] = value
        expect_error(lambda t=tampered: verify_signature(t, lookup_ok, now=NOW),
                     SigningError, "altered")

    # signature-block attacks
    bad_kind = dict(signed)
    bad_kind["signature"] = dict(signed["signature"], kind="buildwars.match_job.v1")
    expect_error(lambda: verify_signature(bad_kind, lookup_ok, now=NOW),
                 SigningError, "wrong-kind")
    swapped_schema = dict(signed)
    swapped_schema["schema"] = "buildwars.runner_capabilities.v1"
    expect_error(lambda: verify_signature(swapped_schema, lookup_ok, now=NOW),
                 SigningError, "wrong-kind")
    no_sig = {k: v for k, v in signed.items() if k != "signature"}
    expect_error(lambda: verify_signature(no_sig, lookup_ok, now=NOW), SigningError)
    extra_field_sig = dict(signed)
    extra_field_sig["signature"] = dict(signed["signature"], nonce=1)
    expect_error(lambda: verify_signature(extra_field_sig, lookup_ok, now=NOW),
                 SigningError, "exactly kind/key_id/value")
    bad_hex = dict(signed)
    bad_hex["signature"] = dict(signed["signature"], value="zz" * 32)
    expect_error(lambda: verify_signature(bad_hex, lookup_ok, now=NOW),
                 SigningError, "malformed")
    short_hex = dict(signed)
    short_hex["signature"] = dict(signed["signature"], value="ab" * 31)
    expect_error(lambda: verify_signature(short_hex, lookup_ok, now=NOW),
                 SigningError, "malformed")

    # foreign key / unknown key id
    expect_error(lambda: verify_signature(signed, lambda kid: None, now=NOW),
                 SigningError, "unknown pairing key")
    expect_error(lambda: verify_signature(signed, lambda kid: fresh, now=NOW),
                 SigningError, "altered")

    # stale + future
    stale = sign_payload(payload, key, signed_at=NOW - 10_000)
    expect_error(lambda: verify_signature(stale, lookup_ok, now=NOW),
                 SigningError, "stale")
    future = sign_payload(payload, key, signed_at=NOW + 10_000)
    expect_error(lambda: verify_signature(future, lookup_ok, now=NOW),
                 SigningError, "future")
    # freshness window boundary honored
    edge = sign_payload(payload, key, signed_at=NOW - 599)
    require(verify_signature(edge, lookup_ok, now=NOW) is not None, "inside window ok")
    late = sign_payload(payload, key, signed_at=NOW - 601)
    expect_error(lambda: verify_signature(late, lookup_ok, now=NOW), SigningError)

    # Exact within-window replay rejects when the caller supplies a guard.
    guard = InMemoryReplayGuard(capacity=8)
    require(verify_signature(signed, lookup_ok, now=NOW, replay_guard=guard),
            "first presentation accepted")
    expect_error(lambda: verify_signature(
        signed, lookup_ok, now=NOW, replay_guard=guard), SigningError, "replay")
    expect_error(lambda: InMemoryReplayGuard(0), ValueError)
    expect_error(lambda: InMemoryReplayGuard(True), ValueError)

    # wrong-user / wrong-runner expectations
    expect_error(
        lambda: verify_signature(signed, lookup_ok, now=NOW,
                                 expect_identity_id=new_id("identity")),
        SigningError, "wrong-user")
    expect_error(
        lambda: verify_signature(signed, lookup_ok, now=NOW,
                                 expect_runner_id=new_id("runner")),
        SigningError, "wrong-runner")
    ok_user = verify_signature(signed, lookup_ok, now=NOW,
                               expect_identity_id=signed["identity_id"])
    require(ok_user is not None, "matching expectation passes")

    # A valid envelope presented under the wrong identity must not burn the
    # replay slot before the correct endpoint verifies it.
    binding_guard = InMemoryReplayGuard(capacity=8)
    expect_error(lambda: verify_signature(
        signed, lookup_ok, now=NOW, replay_guard=binding_guard,
        expect_identity_id=new_id("identity")), SigningError, "wrong-user")
    require(verify_signature(
        signed, lookup_ok, now=NOW, replay_guard=binding_guard,
        expect_identity_id=signed["identity_id"]), "wrong binding did not burn slot")

    # No coercion at signing or verification boundaries.
    expect_error(lambda: sign_payload(payload, key, signed_at=1.5), SigningError)
    expect_error(lambda: sign_payload(payload, key, signed_at=True), SigningError)
    expect_error(lambda: sign_payload(payload, object()), SigningError)
    expect_error(lambda: sign_payload(dict(payload, schema="buildwars.unknown.v1"), key),
                 SigningError, "signable")
    expect_error(lambda: sign_payload(identity_payload(), key),
                 SigningError, "signable")
    expect_error(lambda: sign_payload(dict(payload, unexpected=True), key),
                 SigningError, "schema")
    expect_error(lambda: verify_signature(signed, lookup_ok, now=NOW,
                                          max_age_s=1.5), SigningError)
    expect_error(lambda: verify_signature(signed, lookup_ok, now=NOW,
                                          max_age_s=True), SigningError)
    expect_error(lambda: verify_signature(signed, lookup_ok, now=1.5), SigningError)

    # constant-time comparison is actually used
    import inspect

    source = inspect.getsource(verify_signature)
    require("compare_digest" in source, "verification must be constant-time")
    # the raw key never appears in an envelope
    require(key.secret.reveal().hex() not in encode_canonical(signed).decode(),
            "raw pairing key never serialized; only its fingerprint")

    # Even a correctly MACed body must pass its strict envelope validator.
    import hashlib
    import hmac
    import provider_hub.signing as signing_mod

    invalid_body = {k: v for k, v in signed.items() if k != "signature"}
    invalid_body["unexpected"] = True
    invalid_mac = hmac.new(
        key.secret.reveal(),
        signing_mod._DOMAIN_SEPARATOR + encode_canonical(invalid_body),
        hashlib.sha256,
    ).hexdigest()
    invalid_signed = dict(
        invalid_body,
        signature={"kind": invalid_body["schema"], "key_id": key.key_id,
                   "value": invalid_mac},
    )
    expect_error(lambda: verify_signature(invalid_signed, lookup_ok, now=NOW),
                 SigningError, "schema")
    print("[PASS] HMAC pairing: tamper/stale/binding/replay/coercion all caught")


# ---------------------------------------------------------------------------
# 5. PKCE
# ---------------------------------------------------------------------------


def check_pkce():
    banner("5 pkce")
    verifier = SecretValue(RFC_VECTOR_VERIFIER)
    require(pkce_mod.challenge_from_verifier(verifier) == RFC_VECTOR_CHALLENGE,
            "RFC 7636 Appendix B deterministic vector")

    live = pkce_mod.new_verifier()
    challenge = pkce_mod.challenge_from_verifier(live)
    require(len(challenge) == 43 and challenge.endswith("=") is False, "S256 shape")
    import base64
    import hashlib

    recomputed = base64.urlsafe_b64encode(
        hashlib.sha256(live.reveal().encode("ascii")).digest()
    ).rstrip(b"=").decode()
    require(challenge == recomputed, "challenge derivation")
    expect_error(lambda: pkce_mod.challenge_from_verifier("short"), pkce_mod.PkceError)
    expect_error(lambda: pkce_mod.challenge_from_verifier("a" * 44 + "!"), pkce_mod.PkceError)
    expect_error(lambda: pkce_mod.challenge_from_verifier(RFC_VECTOR_VERIFIER + "x" * 90),
                 pkce_mod.PkceError)
    expect_error(lambda: pkce_mod.assert_plain_challenge_rejected("plain"),
                 pkce_mod.PkceError, "plain")
    pkce_mod.assert_plain_challenge_rejected("S256")  # the only permitted method

    generated_path = pkce_mod.new_callback_path()
    require(
        generated_path.startswith("/buildwars/callback/")
        and len(generated_path.rsplit("/", 1)[-1]) == 22,
        "callback helper generates a 128-bit correlation path",
    )

    callback = "http://127.0.0.1:8765/callback/unpredictable-path-token"
    url = pkce_mod.build_authorize_url(
        callback_url=callback,
        code_challenge=RFC_VECTOR_CHALLENGE,
    )
    parsed_authorize = urllib.parse.urlsplit(url)
    authorize_query = urllib.parse.parse_qs(parsed_authorize.query)
    require(parsed_authorize.scheme == "https" and
            parsed_authorize.netloc == "openrouter.ai" and
            parsed_authorize.path == "/auth", "authorization endpoint pinned")
    require(set(authorize_query) == {
        "callback_url", "code_challenge", "code_challenge_method"
    }, "authorization uses exactly the official OpenRouter fields")
    require(authorize_query["callback_url"] == [callback], "callback_url exact")
    require(authorize_query["code_challenge"] == [RFC_VECTOR_CHALLENGE],
            "challenge exact")
    require(authorize_query["code_challenge_method"] == ["S256"], "S256 pinned")
    for invented in ("client_id", "redirect_uri", "response_type", "scope", "state"):
        require(invented not in authorize_query, f"must not invent {invented}")
    expect_error(lambda: pkce_mod.build_authorize_url(
        callback_url=callback, code_challenge="tooshort"), pkce_mod.PkceError)
    expect_error(lambda: pkce_mod.build_authorize_url(
        callback_url=callback + "?state=not-supported",
        code_challenge=RFC_VECTOR_CHALLENGE), pkce_mod.PkceError, "query")
    for endpoint in (
        "https://evil.example/auth",
        "http://openrouter.ai/auth",
        "https://openrouter.ai/not-auth",
    ):
        with mock.patch.object(pkce_mod, "AUTHORIZE_ENDPOINT", endpoint):
            expect_error(lambda: pkce_mod.build_authorize_url(
                callback_url=callback, code_challenge=RFC_VECTOR_CHALLENGE),
                pkce_mod.PkceError)

    # Callback is correlated by the exact expected callback base URL. OpenRouter
    # documents a code parameter, not a provider-echoed generic OAuth state.
    good_code = "authcode-abc123XYZ._~-09"
    ok_uri = callback + "?code=" + urllib.parse.quote(good_code, safe="")
    code = pkce_mod.parse_callback(ok_uri, expected_callback=callback)
    require(code.reveal() == good_code, "happy-path code extracted")
    require(good_code not in repr(code), "code stays wrapped")

    hostile_pairs = [
        ("http://example.com:8765/callback/unpredictable-path-token?code=" + good_code,
         callback),
        ("http://127.0.0.1/callback/unpredictable-path-token?code=" + good_code,
         callback),
        ("http://127.0.0.1:9999/callback/unpredictable-path-token?code=" + good_code,
         callback),
        ("http://127.0.0.1:8765/callback/other?code=" + good_code, callback),
        (callback, callback),
        (callback + "?code=short", callback),
        (callback + "?code=" + good_code + "&extra=1", callback),
        (callback + "?code=" + good_code + "&code=" + good_code, callback),
        (callback + "?code=a%20b%20c%20d", callback),
        (callback + "#frag", callback),
        (ok_uri, callback + "?unsupported=1"),
    ]
    for actual, expected in hostile_pairs:
        expect_error(lambda a=actual, e=expected: pkce_mod.parse_callback(
            a, expected_callback=e), pkce_mod.PkceError)
    for host in ("[::1]", "localhost"):
        expected = f"http://{host}:8081/cb/path-token"
        actual = expected + "?code=" + urllib.parse.quote(good_code, safe="")
        require(pkce_mod.parse_callback(
            actual, expected_callback=expected).reveal() == good_code,
            f"loopback {host} accepted")
    https_callback = "https://runner.customer.example/cb/path-token"
    require(pkce_mod.parse_callback(
        https_callback + "?code=" + good_code,
        expected_callback=https_callback).reveal() == good_code,
        "exact HTTPS callback accepted")
    expect_error(lambda: pkce_mod.validate_redirect_uri(
        "https://user:pass@host/cb"), pkce_mod.PkceError, "userinfo")
    expect_error(lambda: pkce_mod.validate_redirect_uri(
        "https://host/cb#frag"), pkce_mod.PkceError, "fragment")
    pkce_mod.reject_off_origin("https://openrouter.ai/safe")
    expect_error(lambda: pkce_mod.reject_off_origin(
        "https://openrouter.ai:444/safe"), pkce_mod.PkceError, "port")
    expect_error(lambda: pkce_mod.reject_off_origin(
        "https://user@openrouter.ai/safe"), pkce_mod.PkceError, "userinfo")
    for invalid_port in ("http://127.0.0.1:99999/cb", "https://host:abc/cb"):
        expect_error(lambda u=invalid_port: pkce_mod.validate_redirect_uri(u),
                     pkce_mod.PkceError, "port")

    # exchange through an injected transport — fully offline
    exchanged_key = "sk-or-v1-EXAMPLE-" + "k" * 40
    captured = {}

    def fake_transport(request, timeout_s=30):
        captured["url"] = request.get_full_url()
        captured["method"] = request.get_method()
        captured["body"] = request.data
        return 200, json.dumps({"key": exchanged_key}).encode()

    code_secret = SecretValue(good_code)
    key_secret = pkce_mod.exchange(code_secret, verifier, transport=fake_transport)
    require(captured["url"] == pkce_mod.EXCHANGE_ENDPOINT, "exchange endpoint")
    require(captured["method"] == "POST", "POST exchange")
    require(json.loads(captured["body"]) == {
        "code": good_code,
        "code_verifier": RFC_VECTOR_VERIFIER,
        "code_challenge_method": "S256",
    }, "exchange body exactly binds code, verifier, and S256")
    require(key_secret.reveal() == exchanged_key, "key unwrapped explicitly")
    require(exchanged_key not in repr(key_secret), "key hidden in repr")
    for optional_user_id in ("user_2yOPcMpKoQhcd4bVgSMlELRaIah", None):
        response = json.dumps(
            {"key": exchanged_key, "user_id": optional_user_id}
        ).encode()
        require(pkce_mod.parse_exchange_response(response).reveal() == exchanged_key,
                "documented optional user_id accepted without exposing the key")

    def failing_transport(request, timeout_s=30):
        raise urllib.error.HTTPError(request.full_url, 429, "slow down", hdrs=None, fp=io.BytesIO(b""))

    err = expect_error(lambda: pkce_mod.exchange(
        code_secret, verifier, transport=failing_transport),
                       pkce_mod.PkceError)
    require("429" in str(err) and good_code not in str(err) and exchanged_key not in str(err),
            "HTTP errors sanitized")

    def exploding_transport(request, timeout_s=30):
        raise ConnectionResetError("reset")

    expect_error(lambda: pkce_mod.exchange(
        code_secret, verifier, transport=exploding_transport),
                 pkce_mod.PkceError, "ConnectionResetError")
    expect_error(lambda: pkce_mod.exchange(
        SecretValue("short"), verifier, transport=fake_transport), pkce_mod.PkceError)
    expect_error(lambda: pkce_mod.exchange(
        code_secret, "raw-verifier", transport=fake_transport), pkce_mod.PkceError)
    expect_error(lambda: pkce_mod.exchange(code_secret, transport=fake_transport), TypeError)

    hostile_responses = [
        b"not json",
        json.dumps({"key": exchanged_key, "error": None}).encode(),   # extra field
        json.dumps({"key": exchanged_key, "user_id": 123}).encode(),
        json.dumps({"key": exchanged_key, "user_id": ""}).encode(),
        json.dumps({"key": exchanged_key, "user_id": "bad\nvalue"}).encode(),
        json.dumps({"id": "x"}).encode(),                             # missing key
        json.dumps({"key": "short"}).encode(),                        # bad shape
        json.dumps({"key": 12345}).encode(),
        json.dumps({"key": "sk-live-" + "k" * 40}).encode(),          # foreign prefix
        json.dumps({"key": exchanged_key}).encode()[:-5],             # truncated json
        b"x" * (pkce_mod._MAX_RESPONSE_BYTES + 1),
    ]
    for raw in hostile_responses:
        expect_error(lambda r=raw: pkce_mod.parse_exchange_response(r), pkce_mod.PkceError)

    def wrong_status_transport(request, timeout_s=30):
        return 500, b"{}"

    expect_error(lambda: pkce_mod.exchange(
        code_secret, verifier, transport=wrong_status_transport),
                 pkce_mod.PkceError, "HTTP 500")

    # The default opener's redirect handler refuses every redirect before a
    # one-time code can be reposted to a different URL.
    handler = pkce_mod._NoRedirectHandler()
    require(handler.redirect_request(None, None, 302, "Found", {},
                                     "https://evil.example/") is None,
            "redirect handler refuses follow-up requests")

    # off-origin exchange endpoint fails closed pre-network
    with mock.patch.object(pkce_mod, "EXCHANGE_ENDPOINT", "http://openrouter.ai/api/x"):
        expect_error(lambda: pkce_mod.exchange(
            code_secret, verifier, transport=fake_transport),
                     pkce_mod.PkceError, "https")
    with mock.patch.object(pkce_mod, "EXCHANGE_ENDPOINT", "https://evil.example/api/keys"):
        expect_error(lambda: pkce_mod.exchange(
            code_secret, verifier, transport=fake_transport),
                     pkce_mod.PkceError, "allowlisted")
    with mock.patch.object(pkce_mod, "EXCHANGE_ENDPOINT",
                           "https://openrouter.ai/api/v1/auth/not-keys"):
        expect_error(lambda: pkce_mod.exchange(
            code_secret, verifier, transport=fake_transport),
            pkce_mod.PkceError, "pinned")
    print("[PASS] official OpenRouter PKCE fields, callback binding, verifier exchange")


# ---------------------------------------------------------------------------
# 6. adapters
# ---------------------------------------------------------------------------


class _RunCapture:
    def __init__(self, stdout=b"", returncode=0, stderr=b""):
        self.calls = []
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return subprocess.CompletedProcess([], self.returncode, stdout=self.stdout,
                                           stderr=self.stderr)


def check_adapters():
    banner("6 adapters")
    sys.path.insert(0, os.path.join(ROOT, "entrants"))
    sys.path.insert(0, ROOT)
    import entrants.backends as backends

    # --- codex ---
    cap = _RunCapture(stdout=b'{"player_id": 12}\n')
    with mock.patch.dict(os.environ, {
            "OPENAI_API_KEY": "must-strip", "AZURE_OPENAI_API_KEY": "strip-too"}), \
            mock.patch("entrants.backends.shutil.which", return_value="/fake/codex"), \
            mock.patch("entrants.backends.subprocess.run", cap):
        out = backends.CodexExecBackend(60).complete("pick one")
    require(out == '{"player_id": 12}', "codex stdout passthrough")
    argv, kwargs = cap.calls[0]
    require(argv[:2] == ["/fake/codex", "exec"], "codex exec subcommand")
    for flag in ("--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
                 "--ignore-rules"):
        require(flag in argv, f"codex safety flag {flag}")
    require(argv[argv.index("--sandbox") + 1] == "read-only", "read-only sandbox")
    require(argv[-1] == "-", "codex reads the prompt from stdin explicitly")
    require(kwargs.get("cwd"), "ephemeral cwd supplied")
    require(not os.path.exists(kwargs["cwd"]), "ephemeral cwd removed after run")
    require(kwargs.get("input") == b"pick one", "prompt travels on stdin")
    require("OPENAI_API_KEY" not in kwargs["env"] and
            "AZURE_OPENAI_API_KEY" not in kwargs["env"], "API env removed")
    require(backends.CodexExecBackend(60).label == "chatgpt_codex:codex exec", "label")
    fail_cap = _RunCapture(returncode=2, stderr=b"sk-" + b"proj-must-not-leak")
    with mock.patch("entrants.backends.shutil.which", return_value="/fake/codex"), \
            mock.patch("entrants.backends.subprocess.run", fail_cap):
        err = expect_error(lambda: backends.CodexExecBackend(60).complete("p"), RuntimeError)
    require("exited 2" in str(err) and "sk-" + "proj" not in str(err),
            "failure surfaces only the exit code")

    # --- claude ---
    cap = _RunCapture(stdout=b"move\n")
    with mock.patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "must-strip", "ANTHROPIC_AUTH_TOKEN": "strip-too"}), \
            mock.patch("entrants.backends.shutil.which", return_value="/fake/claude"), \
            mock.patch("entrants.backends.subprocess.run", cap):
        backends.ClaudePrintBackend(60).complete("pick one")
    argv, kwargs = cap.calls[0]
    require(argv[0] == "/fake/claude" and argv[1] == "-p", "non-interactive print mode")
    for flag in ("--output-format", "--max-turns", "--strict-mcp-config",
                 "--no-session-persistence", "--safe-mode", "--tools"):
        require(flag in argv, f"claude safety flag {flag}")
    require(argv[argv.index("--output-format") + 1] == "text", "text output")
    require(argv[argv.index("--max-turns") + 1] == "1", "single turn")
    require(argv[argv.index("--tools") + 1] == "", "built-in tools disabled")
    require("--fallback-model" not in argv, "no fallback model configured")
    require("ANTHROPIC_API_KEY" not in kwargs["env"] and
            "ANTHROPIC_AUTH_TOKEN" not in kwargs["env"], "API env removed")
    require(backends.ClaudePrintBackend(60).label == "claude_code:claude -p", "label")

    # --- legacy opencode remains byte-compatible when --provider is omitted ---
    expect_error(lambda: backends.OpenCodeBackend("has space"), ValueError)
    require(backends.OpenCodeBackend("-leading-dash").label ==
            "opencode:-leading-dash@max", "legacy leading-dash acceptance preserved")
    require(backends.OpenCodeBackend("m@double@dash").label ==
            "opencode:m@double@dash@max", "legacy direct constructor preserved")
    event = json.dumps({"type": "text", "part": {"text": "hi"}}).encode() + b"\n"
    cap = _RunCapture(stdout=event)
    with mock.patch("entrants.backends.shutil.which", return_value="/fake/opencode"), \
            mock.patch("entrants.backends.subprocess.run", cap):
        require(backends.OpenCodeBackend("vendor/model", "max").complete("p") == "hi",
                "existing opencode behavior preserved")
    argv, _ = cap.calls[0]
    require(argv[:4] == ["/fake/opencode", "run", "-m", "vendor/model"], "opencode argv head")

    # --- provider opencode is a separate contained adapter ---
    cap = _RunCapture(stdout=event)
    with mock.patch("entrants.backends.shutil.which", return_value="/fake/opencode"), \
            mock.patch("entrants.backends.subprocess.run", cap):
        provider_oc = backends.OpenCodeProviderBackend("vendor/model", "max", 60)
        require(provider_oc.complete("choose") == "hi", "contained provider output")
    argv, kwargs = cap.calls[0]
    require(argv[0] == "/fake/opencode" and argv[1] == "run", "provider run")
    require("--pure" in argv and "--auto" not in argv, "pure without auto approval")
    require(argv[-2:] == ["--", "choose"], "prompt is a positional after option terminator")
    require(kwargs.get("input") is None and kwargs.get("stdin") is subprocess.DEVNULL,
            "provider OpenCode does not rely on undocumented stdin prompts")
    require(kwargs.get("cwd") and not os.path.exists(kwargs["cwd"]),
            "OpenCode provider cwd removed")
    child_env = kwargs["env"]
    for name in ("OPENCODE_CONFIG_CONTENT", "OPENCODE_DISABLE_PROJECT_CONFIG",
                 "OPENCODE_PURE", "OPENCODE_AUTO_SHARE",
                 "OPENCODE_DISABLE_EXTERNAL_SKILLS",
                 "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS"):
        require(name in child_env, f"contained OpenCode env {name}")
    policy = json.loads(child_env["OPENCODE_CONFIG_CONTENT"])
    require(policy["permission"]["*"] == "deny", "default deny policy")
    require(policy["agent"][provider_oc.AGENT_NAME]["permission"]["*"] == "deny",
            "selected agent inherits default deny")
    expect_error(
        lambda: backends.OpenCodeProviderBackend("noslash"),
        ValueError,
        "provider/model",
    )

    # --- openrouter ---
    require(backends.OpenRouterChatBackend.ENV_VAR == "OPENROUTER_API_KEY", "env name")
    sentinel_key = "sk-" + "or-v1-EXAMPLE-openrouter-sentinel"
    seen_auth = []

    def net_capture(request, timeout_s=300):
        for name, value in request.header_items():
            if name.lower() == "authorization":
                seen_auth.append(value)
        return json.dumps(
            {"choices": [{"message": {"content": " alloc "}}]}
        ).encode()

    backend = backends.OpenRouterChatBackend("vendor/model-x", transport=net_capture)
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": sentinel_key}):
        require(backend.complete("alloc") == "alloc", "content stripped+returned")
    require(seen_auth == [f"Bearer {sentinel_key}"], "key rides only the auth header")
    require(backend.label == "openrouter:vendor/model-x" and
            sentinel_key not in backend.label, "label never holds key")

    def net_missing_content(request, timeout_s=300):
        return json.dumps({"choices": []}).encode()

    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": sentinel_key}):
        b2 = backends.OpenRouterChatBackend("m", transport=net_missing_content)
        expect_error(lambda: b2.complete("x"), RuntimeError, "assistant content")

    def net_http_error(request, timeout_s=300):
        raise urllib.error.HTTPError(request.full_url, 401, "nope", hdrs=None,
                                     fp=io.BytesIO(b""))

    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": sentinel_key}):
        b3 = backends.OpenRouterChatBackend("m", transport=net_http_error)
        err = expect_error(lambda: b3.complete("x"), RuntimeError)
        require("401" in str(err) and sentinel_key not in str(err), "key absent from errors")

    with mock.patch.dict(os.environ, {}, clear=True):
        b4 = backends.OpenRouterChatBackend("m", transport=net_capture)
        err = expect_error(lambda: b4.complete("x"), RuntimeError, "OPENROUTER_API_KEY")
        require(sentinel_key not in str(err), "unset env error clean")
    expect_error(lambda: backends.OpenRouterChatBackend("-bad model"), ValueError)
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "bad\r\nheader"}):
        err = expect_error(lambda: backends.OpenRouterChatBackend(
            "m", transport=net_capture).complete("x"), RuntimeError, "unsafe shape")
        require("bad" not in str(err), "unsafe key not echoed")
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": sentinel_key}):
        oversized = backends.OpenRouterChatBackend(
            "m", transport=lambda request, timeout_s=300:
            b"x" * (backends.OpenRouterChatBackend.MAX_RESPONSE_BYTES + 1))
        expect_error(lambda: oversized.complete("x"), RuntimeError, "size cap")
        with mock.patch.object(backends.OpenRouterChatBackend, "ENDPOINT",
                               "https://openrouter.ai/other"):
            expect_error(lambda: backends.OpenRouterChatBackend(
                "m", transport=net_capture).complete("x"), RuntimeError, "pinned")

    # --- hermes ---
    cap = _RunCapture(stdout=b'{"allocation":[1]*10}\n')
    with mock.patch("entrants.backends.shutil.which", return_value="/fake/hermes"), \
            mock.patch("entrants.backends.subprocess.run", cap):
        out = backends.HermesOneshotBackend("vendor/model-x", timeout_s=60).complete("commit")
    argv, kwargs = cap.calls[0]
    require(argv == ["/fake/hermes", "--oneshot", "--provider", "vendor",
                     "--model", "vendor/model-x", "--ignore-rules", "--safe-mode",
                     "--toolsets", "clarify", "commit"], "hermes argv exact")
    require(kwargs.get("input") is None and kwargs.get("stdin") is subprocess.DEVNULL,
            "Hermes receives --oneshot prompt as argv, not stdin")
    require(backends.HermesOneshotBackend("vendor/model-x").label
            == "hermes:vendor/model-x", "label")
    expect_error(lambda: backends.HermesOneshotBackend("noslash"), ValueError, "provider/model")
    expect_error(lambda: backends.HermesOneshotBackend("/leadingslash"), ValueError)
    expect_error(lambda: backends.HermesOneshotBackend("vendor/-dashy"), ValueError, "'-'")

    # --- custom agent escape hatch ---
    cli = backends.get_provider_backend("custom_agent", command=["myagent", "--serve"])
    require(isinstance(cli, backends.CustomerCommandBackend), "custom backend exact")
    require(cli.label == "custom_cli:myagent", "custom label")
    cap = _RunCapture(stdout=b"answer\n")
    with mock.patch("entrants.backends.shutil.which", return_value="/fake/myagent"), \
            mock.patch("entrants.backends.subprocess.run", cap):
        require(cli.complete("question") == "answer", "custom prompt/stdout route")
    argv, kwargs = cap.calls[0]
    require(argv == ["/fake/myagent", "--serve"] and kwargs["input"] == b"question",
            "custom JSON argv and stdin are exact")
    require(kwargs["cwd"] is None, "customer command retains caller cwd intentionally")
    expect_error(lambda: backends.get_provider_backend("custom_agent"), ValueError,
                 "explicit JSON argv")
    expect_error(lambda: backends.get_provider_backend("custom_agent", command=[""]),
                 ValueError)
    expect_error(lambda: backends.get_provider_backend(
        "custom_agent", command=["x"], model="ignored"), ValueError, "does not accept")

    # --- resolution table ---
    for pid, cls in (
        ("chatgpt_codex", backends.CodexExecBackend),
        ("claude_code", backends.ClaudePrintBackend),
        ("opencode", backends.OpenCodeProviderBackend),
        ("openrouter", backends.OpenRouterChatBackend),
        ("hermes", backends.HermesOneshotBackend),
    ):
        kwargs = {"model": "vendor/model"} if pid in ("opencode", "openrouter", "hermes") else {}
        require(isinstance(backends.get_provider_backend(pid, **kwargs), cls),
                f"{pid} resolves to its catalog-declared adapter kind")
    require(backends.execution_claim_for_provider("chatgpt_codex") == "model",
            "provider adapters claim model execution")
    expect_error(lambda: backends.get_provider_backend("totally_unknown"), ProviderError)
    expect_error(lambda: backends.get_provider_backend("opencode"), ValueError, "provider-model")
    expect_error(lambda: backends.get_provider_backend(
        "chatgpt_codex", model="silently-ignored"), ValueError, "does not accept")
    expect_error(lambda: backends.get_provider_backend(
        "openrouter", model="m", variant="ignored"), ValueError, "does not accept")
    for bad_timeout in (0, -1, float("nan"), float("inf"), True, 3601):
        expect_error(lambda t=bad_timeout: backends.get_provider_backend(
            "chatgpt_codex", timeout_s=t), ValueError)
    expect_error(lambda: backends.execution_claim_for_provider("nope"), ProviderError)

    # adapters never touch provider_hub credentials: they read only this process env
    src = open(os.path.join(ROOT, "entrants", "backends.py"), encoding="utf-8").read()
    for banned in ("~/.codex", "auth.json", ".claude.json", "credentials.json",
                   "OPENROUTER_API_KEY=",):
        require(banned not in src, f"backends must not reference {banned}")
    print("[PASS] adapter argv/env/label contracts under mocks only")


# ---------------------------------------------------------------------------
# 7. harness integration
# ---------------------------------------------------------------------------


class FixedBackend:
    label = "fixture:fixed"

    def __init__(self, response):
        self.response = response

    def complete(self, _prompt):
        return self.response


def _namespace(**kw):
    import argparse

    defaults = dict(backend=None, provider=None, provider_model=None,
                    provider_variant=None, provider_command=None,
                    backend_timeout=None)
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def check_harnesses():
    banner("7 harnesses")
    import entrants.fantasy_model_harness as fantasy
    import entrants.ten_fronts_model_harness as fronts
    from entrants.backends import get_backend

    # provider choices identical in both harnesses
    require(fantasy.PROVIDER_CHOICES == fronts.PROVIDER_CHOICES, "choice parity")
    require(set(fantasy.PROVIDER_CHOICES) == set(PROVIDER_IDS), "choices equal catalog")

    # mutual exclusion + requirement rules
    expect_error(lambda: fantasy.build_backend(_namespace()), SystemExit)
    expect_error(lambda: fantasy.build_backend(
        _namespace(backend="stub:v1", provider="hermes")), SystemExit)
    expect_error(lambda: fantasy.build_backend(_namespace(provider="hermes")), SystemExit)

    # byte-for-byte legacy behavior when provider omitted
    b = fantasy.build_backend(_namespace(backend="stub:v1"))
    require(b.label == "stub:v1", "legacy spec unchanged")
    b = fronts.build_backend(_namespace(backend="opencode:m@fast", backend_timeout=99))
    require(b.label == "opencode:m@fast" and b.timeout_s == 99, "legacy opencode spec")
    b = fantasy.build_backend(_namespace(backend="cli:myagent --serve"))
    require(b.label == "cli:myagent", "legacy cli spec")

    # provider selection resolves through the catalog
    b = fronts.build_backend(_namespace(provider="chatgpt_codex", backend_timeout=42))
    require(type(b).__name__ == "CodexExecBackend" and b.timeout_s == 42, "codex selection")
    b = fantasy.build_backend(_namespace(provider="opencode", provider_model="v/m",
                                         provider_variant="fast"))
    require(b.label == "opencode-provider:v/m@fast", "variant flows through")
    command_json = json.dumps([sys.executable, "-c", "print('ok')"])
    b = fronts.build_backend(_namespace(
        provider="custom_agent", provider_command=command_json))
    require(type(b).__name__ == "CustomerCommandBackend" and
            b.command[0] == sys.executable, "custom JSON argv flows through")
    expect_error(lambda: fronts.build_backend(_namespace(
        provider="custom_agent", provider_command="not-json")), SystemExit)
    expect_error(lambda: fronts.build_backend(_namespace(
        provider="openrouter", provider_model="v/m", provider_variant="ignored")),
        SystemExit)

    # end-to-end provider-backed decision with mocked network: source=model truth
    from arena.games import load as load_game
    import random as _random

    game = load_game("fantasy_redraft")
    state = game.setup(_random.Random(9201))
    observation = game.observation(state, 0)
    legal_player = fantasy.legal_players(observation)[0]
    legal = json.dumps({"player_id": legal_player["id"]}, separators=(",", ":"))

    def chat_transport(request, timeout_s=300):
        return json.dumps({"choices": [{"message": {"content": legal}}]}).encode()

    def broken_transport(request, timeout_s=300):
        raise ConnectionResetError("down")

    import entrants.backends as backends

    with mock.patch.dict(
        os.environ,
        {"OPENROUTER_API_KEY": "sk-" + "or-v1-EXAMPLE-harness"},
    ):
        provider_backend = fantasy.build_backend(
            _namespace(provider="openrouter", provider_model="vendor/model"))
        provider_backend._transport = chat_transport
        move, note = fantasy.decide(observation, "win-now", provider_backend)
        require(note.startswith("source=model;"), f"honest model source: {note}")
        require(fantasy.move_is_legal_for_observation(observation, move), "legal pick")

        # provider failure keeps deterministic legal fallback and honest reason
        provider_backend._transport = broken_transport
        move, note = fantasy.decide(observation, "win-now", provider_backend)
        require(note.startswith("source=fallback;reason=backend_error:RuntimeError"),
                f"sanitized failure reason: {note}")
        require(fantasy.move_is_legal_for_observation(observation, move), "fallback legal")
        require("sk-or-v1" not in note, "no key fragments in notes")

    # ten fronts: provider selection + mocked subprocess (hermes) end-to-end
    alloc = json.dumps({"allocation": [10] * 10})
    cap = _RunCapture(stdout=alloc.encode())
    with mock.patch("entrants.backends.shutil.which", return_value="/fake/hermes"), \
            mock.patch("entrants.backends.subprocess.run", cap):
        hb = fronts.build_backend(_namespace(provider="hermes", provider_model="vendor/m"))
        obs_tf = {"phase": "commit", "round": 1, "front_values": [1] * 10, "history": []}
        move, note = fronts.decide(obs_tf, "even-pressure", hb)
        require(note.startswith("source=model;"), f"hermes sourced: {note}")
        require(move["allocation"] == [10] * 10, "allocation parsed")

    # invalid provider output still falls back legally with response digest kept
    cap = _RunCapture(stdout=b"garbage from a model")
    with mock.patch("entrants.backends.shutil.which", return_value="/fake/hermes"), \
            mock.patch("entrants.backends.subprocess.run", cap):
        hb = fronts.build_backend(_namespace(provider="hermes", provider_model="vendor/m"))
        move, note = fronts.decide(obs_tf, "even-pressure", hb)
        require(note.startswith("source=fallback;reason=invalid_model_output;"),
                f"invalid output falls back: {note}")
        require("response_sha256=" in note, "response digest retained for audit")
        require(fronts.allocation_is_legal(move["allocation"]), "fallback allocation legal")

    # wire-level byte-for-byte regression for the omitted-provider path
    def wire(script, args, lines):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, script)] + args,
            input=("\n".join(lines) + "\n").encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
        )
        require(proc.returncode == 0, f"{script} wire exit {proc.returncode}: {proc.stderr[-200:]}")
        return proc.stdout.decode("utf-8")

    tf_script = os.path.join("entrants", "ten_fronts_model_harness.py")
    obs_line = json.dumps({"type": "move_request", "observation": {
        "phase": "signal", "round": 1, "front_values": [1] * 10, "history": []}})
    out = wire(tf_script, ["--backend", "stub:v1", "--strategy", "value-blitz",
                           "--name", "Pin"], [json.dumps({"type": "hello"}), obs_line])
    lines_out = out.strip().splitlines()
    require(lines_out[0] == '{"type":"ready","entrant":"Pin","version":"1","backend":"stub:v1"}',
            f"ready line pinned: {lines_out[0]}")
    require('"note":"source=' in lines_out[1], "move line carries source note")

    fan_script = os.path.join("entrants", "fantasy_model_harness.py")
    out = wire(fan_script, ["--backend", "stub:v1", "--strategy", "win-now",
                            "--name", "Pin"], [json.dumps({"type": "hello"})])
    require(out.strip() == '{"type":"ready","entrant":"Pin","version":"1","backend":"stub:v1"}',
            "fantasy ready line pinned")
    print("[PASS] provider selection in both harnesses; legacy path byte-pinned")


# ---------------------------------------------------------------------------
# 8. manifest env names only
# ---------------------------------------------------------------------------


def check_manifest_env_names():
    banner("8 manifests")
    from arena.match import validate_manifest
    from arena.sandbox import Entrant

    base = {
        "name": "Provider Entrant",
        "cmd": [sys.executable, os.path.join(ROOT, "entrants", "fantasy_model_harness.py"),
                "--strategy", "win-now", "--name", "Provider Entrant",
                "--provider", "openrouter", "--provider-model", "vendor/model"],
        "env": ["OPENROUTER_API_KEY"],
        "claimed_model": "customer-openrouter:vendor/model",
        "execution_claim": "model",
    }
    validate_manifest(base)
    fake_inline_secret = "sk-" + "or-v1-EXAMPLE-leak"
    expect_error(
        lambda: validate_manifest(
            dict(base, env=["OPENROUTER_API_KEY=" + fake_inline_secret])
        ),
        ValueError, "names")

    sentinel = "sk-" + "or-v1-EXAMPLE-manifest-sentinel"
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": sentinel}):
        entrant = Entrant(base, workdir=os.path.join(ROOT, "__pycache__"))
        child_env = entrant._child_env()
    require(child_env.get("OPENROUTER_API_KEY") == sentinel,
            "sandbox passes DECLARED names from parent env, values untouched")
    require("OPENROUTER_API_KEY=" + "sk-" + "or" not in encode_canonical(base).decode(),
            "manifest bytes carry the name, never a literal value")

    # shipped docs/templates never embed a concrete credential value
    for relpath in (
        os.path.join("docs", "PROVIDER_CONNECTIONS.md"),
        os.path.join("template", "entrant.toml"),
        os.path.join("template", "README.md"),
        os.path.join("AGENTWARS_PROVIDER_HUB_RELEASE.md"),
        os.path.join("bin", "buildwars_provider.py"),
        os.path.join("bin", "check_provider_hub.py"),
    ):
        path = os.path.join(ROOT, relpath)
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        for marker in re.finditer(r"sk-or-[A-Za-z0-9-]{16,}", text):
            require(marker.group(0).startswith("sk-or-v1-EXAMPLE") or "EXAMPLE" in marker.group(0),
                    f"{relpath} must contain only placeholder keys, found {marker.group(0)[:20]}")
    print("[PASS] manifests and docs carry env names, never values")


# ---------------------------------------------------------------------------
# 9. arena purity guard
# ---------------------------------------------------------------------------

_FORBIDDEN_IMPORT_ROOTS = {
    "urllib", "http", "socket", "ssl", "requests", "httpx", "aiohttp", "ftplib",
    "smtplib", "telnetlib", "asyncio",
    "provider_hub", "entrants", "bin",
}
_FORBIDDEN_NAME_TOKENS = {"oauth", "api_key", "apikey", "bearer", "openrouter",
                          "provider_hub"}
_FORBIDDEN_STRING_MARKERS = [
    "bearer ", "authorization:", "oauth", "sk-or-v1", "sk-ant-", "api.openai.com",
    "anthropic.com", "openrouter.ai", "provider_hub", "~/.codex", "auth.json",
]


def check_arena_purity():
    banner("9 arena purity")
    arena_dir = os.path.join(ROOT, "arena")
    scanned = 0
    for dirpath, _dirnames, filenames in os.walk(arena_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            scanned += 1
            path = os.path.join(dirpath, filename)
            rel = os.path.relpath(path, ROOT)
            source = open(path, encoding="utf-8").read()
            tree = ast.parse(source, filename=rel)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_name = alias.name.split(".")[0]
                        require(root_name not in _FORBIDDEN_IMPORT_ROOTS,
                                f"{rel}: forbidden import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    root_name = (node.module or "").split(".")[0]
                    if node.level == 0:
                        require(root_name not in _FORBIDDEN_IMPORT_ROOTS,
                                f"{rel}: forbidden import from {node.module}")
                elif isinstance(node, ast.Name):
                    require(node.id.lower() not in _FORBIDDEN_NAME_TOKENS,
                            f"{rel}: forbidden identifier {node.id}")
                elif isinstance(node, ast.Constant):
                    value = node.value
                    if isinstance(value, str):
                        lowered = value.lower()
                        for marker in _FORBIDDEN_STRING_MARKERS:
                            require(marker not in lowered,
                                    f"{rel}: forbidden string marker {marker!r}")

            require("provider_hub" not in source, f"{rel}: textual provider_hub reference")
            require("import entrants" not in source, f"{rel}: textual entrants import")
    require(scanned >= 10, f"expected to scan the arena package, scanned {scanned}")

    # reverse direction: the hub never imports the engine either
    hub_dir = os.path.join(ROOT, "provider_hub")
    for filename in os.listdir(hub_dir):
        if not filename.endswith(".py"):
            continue
        source = open(os.path.join(hub_dir, filename), encoding="utf-8").read()
        require("import arena" not in source and "from arena" not in source,
                f"provider_hub/{filename} must not import the engine")
    print(f"[PASS] {scanned} arena modules hold no provider/HTTP/socket/token dependency")


# ---------------------------------------------------------------------------
# 10. regression ladder
# ---------------------------------------------------------------------------

_PY_COMPILE_TARGETS = [
    "provider_hub/__init__.py",
    "provider_hub/catalog.py",
    "provider_hub/ids.py",
    "provider_hub/pkce.py",
    "provider_hub/schemas.py",
    "provider_hub/secrets.py",
    "provider_hub/signing.py",
    "entrants/backends.py",
    "entrants/fantasy_model_harness.py",
    "entrants/ten_fronts_model_harness.py",
    "bin/buildwars_provider.py",
    "bin/check_provider_hub.py",
]

_LADDER = [
    [sys.executable, "bin/check_agentwars_scale.py"],
    [sys.executable, "bin/check_share_bundle.py"],
    [sys.executable, "bin/check_agentwars_product.py"],
    # NOTE: the release packet names bin/check_ten_fronts_contract.py; the repo
    # ships bin/check_ten_fronts.py — running the shipped file and recording the drift.
    [sys.executable, "bin/check_ten_fronts.py"],
    [sys.executable, "bin/check_fantasy_games.py"],
    [sys.executable, "bin/selfcheck.py"],
    [sys.executable, "bin/build_verifier.py", "--check"],
]


def check_ladder():
    banner("10 regression ladder")
    for target in _PY_COMPILE_TARGETS:
        proc = subprocess.run(
            [sys.executable, "-m", "py_compile", os.path.join(ROOT, target)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        require(proc.returncode == 0, f"py_compile failed for {target}: {proc.stdout}")
    print(f"[PASS] py_compile clean for {len(_PY_COMPILE_TARGETS)} claimed files")

    for cmd in _LADDER:
        proc = subprocess.run(
            cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        require(proc.returncode == 0,
                f"ladder failed: {' '.join(cmd)}\n{proc.stdout[-800:]}")
        print(f"[PASS] {os.path.basename(cmd[1])} {' '.join(cmd[2:])} :: {tail[-72:]}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run adversarial contracts for the BuildWars provider hub."
    )
    parser.add_argument(
        "--skip-regressions",
        action="store_true",
        help="run provider-hub contract sections without the full repository ladder",
    )
    args = parser.parse_args(argv)
    started = time.time()
    check_catalog()
    check_schemas()
    check_secrets()
    check_signing()
    check_pkce()
    check_adapters()
    check_harnesses()
    check_manifest_env_names()
    check_arena_purity()
    if args.skip_regressions:
        print("[SKIP] full repository regression ladder")
    else:
        check_ladder()
    elapsed = time.time() - started
    print()
    print(f"BuildWars provider hub: ALL SECTIONS PASS ({elapsed:.1f}s)")
    print("six providers / strict envelopes / constant-time pairing / offline PKCE /")
    ladder_status = "regression ladder skipped" if args.skip_regressions else "green ladder"
    print(f"mocked-only adapters / honest fallback counts / pure arena / {ladder_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
