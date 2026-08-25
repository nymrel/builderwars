#!/usr/bin/env python3
"""Hostile local checks for AgentWars runner pairing and request signing.

No provider is contacted.  HTTP exercises a literal 127.0.0.1 test server;
all state lives in a temporary directory and is removed on exit.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import faulthandler
import hashlib
import http.server
import importlib.util
import io
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from cryptography.exceptions import InvalidSignature  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from provider_hub.local_runner import (  # noqa: E402
    MAX_HTTP_BYTES,
    PAIRING_CLAIM_PATH,
    REQUEST_PROTOCOL,
    RUNNER_PROBE_BODY,
    RUNNER_PROBE_FALSE_ATTESTATIONS,
    RUNNER_PROBE_PATH,
    RunnerClientError,
    RunnerHttpError,
    canonical_runner_request,
    claim_runner,
    digest_harness_file,
    public_key_material,
    parse_pairing_secret,
    send_signed_request,
    sign_runner_request,
    validate_claim_response,
    validate_json_body,
    validate_origin,
    validate_probe_response,
)
from provider_hub.runner_state import RunnerStateError, RunnerStateStore  # noqa: E402


CHECKS = 0
RUNNER_ID = "awr1_" + "R" * 22
CHALLENGE_ID = "C" * 22
PAIRING_SECRET = f"awp1_{CHALLENGE_ID}_{'S' * 32}"
PASSPHRASE = b"correct horse battery staple"
TRUST_FLAGS = (
    "providerAccountAttested",
    "planEntitlementAttested",
    "billingRouteAttested",
    "modelAttested",
    "personAttested",
    "runtimeAttested",
    "harnessExecutionAttested",
    "matchExecutionAttested",
)


def check(condition, label):
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def expect_error(action, error_type, message_part=None, *, forbid=()):
    try:
        action()
    except error_type as error:
        rendered = str(error)
        if message_part is not None:
            check(message_part in rendered, f"error contains {message_part!r}")
        for forbidden in forbid:
            if isinstance(forbidden, bytes):
                forbidden = forbidden.decode("utf-8", errors="replace")
            check(str(forbidden) not in rendered, "error does not echo supplied secret")
        return error
    raise AssertionError(f"expected {error_type.__name__}")


def decode_base64url(value):
    return base64.urlsafe_b64decode(value + "=" * ((4 - len(value) % 4) % 4))


class ServerState:
    def __init__(self):
        self.mode = "ok"
        self.claim_requests = []
        self.signed_requests = []
        self.redirect_hits = 0
        self.public_key = None
        self.nonces = set()
        self.accepted_claims = 0


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "AgentWarsCheck/1"

    def log_message(self, _format, *_args):
        return

    @property
    def state(self):
        return self.server.agentwars_state

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if self.path == "/redirect-target":
            self.state.redirect_hits += 1
            self._json(200, {"unexpected": True})
            return
        if self.path == PAIRING_CLAIM_PATH:
            self._claim(body)
            return
        if self.path == RUNNER_PROBE_PATH:
            self._signed(body)
            return
        self._json(404, {"error": "not_found"})

    def _claim(self, body):
        self.state.claim_requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers.items()),
                "body": body,
            }
        )
        if self.state.mode == "redirect":
            self.send_response(307)
            self.send_header("Location", "/redirect-target")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.state.mode == "non_json":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if self.state.mode == "oversize":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(MAX_HTTP_BYTES + 1))
            self.end_headers()
            return
        if self.state.mode == "chunked_oversize":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            raw = b"x" * (MAX_HTTP_BYTES + 1)
            self.wfile.write(f"{len(raw):x}\r\n".encode("ascii") + raw + b"\r\n0\r\n\r\n")
            return
        request = json.loads(body.decode("utf-8"))
        challenge_id, _random_code = parse_pairing_secret(request["pairingSecret"])
        if self.state.mode == "drop_after_accept":
            self.state.accepted_claims += 1
            self.close_connection = True
            with contextlib.suppress(OSError):
                self.connection.shutdown(socket.SHUT_RDWR)
            return
        if self.state.mode == "server_error":
            self._json(503, {"error": "echo", "detail": request["pairingSecret"]})
            return
        self.state.public_key = request["publicKey"]
        response = {
            "schemaVersion": 1,
            "protocolVersion": "agentwars.runner_pairing.v1",
            "status": "claimed",
            "challengeId": challenge_id,
            "state": "pending_confirmation",
            "fingerprint": hashlib.sha256(decode_base64url(request["publicKey"])).hexdigest(),
        }
        if self.state.mode == "mismatch":
            response["fingerprint"] = "0" * 64
        if self.state.mode == "unknown_key":
            response["extra"] = True
        if self.state.mode == "duplicate_key":
            raw = (
                '{"schemaVersion":1,"schemaVersion":1,'
                '"protocolVersion":"agentwars.runner_pairing.v1",'
                '"status":"claimed","challengeId":"' + challenge_id + '",'
                '"state":"pending_confirmation","fingerprint":"' + response["fingerprint"] + '"}'
            ).encode("utf-8")
            self._raw_json(200, raw)
            return
        self._json(200 if self.state.mode == "wrong_status" else 202, response)

    def _signed(self, body):
        headers = {key.lower(): value for key, value in self.headers.items()}
        nonce = headers.get("agentwars-nonce")
        if nonce in self.state.nonces:
            self._json(409, {"error": "replay"})
            return
        try:
            canonical = canonical_runner_request(
                method="POST",
                path=self.path,
                body_sha256=hashlib.sha256(body).hexdigest(),
                timestamp=headers["agentwars-timestamp"],
                nonce=nonce,
                runner_id=headers["agentwars-runner-id"],
            )
            public = Ed25519PublicKey.from_public_bytes(decode_base64url(self.state.public_key))
            public.verify(
                decode_base64url(headers["agentwars-signature"]),
                canonical.encode("utf-8"),
            )
        except (KeyError, ValueError, InvalidSignature, RunnerClientError):
            self._json(401, {"error": "invalid_signature"})
            return
        self.state.nonces.add(nonce)
        self.state.signed_requests.append(
            {"body": body, "headers": headers, "canonical": canonical}
        )
        response = {
            "schemaVersion": 1,
            "protocolVersion": REQUEST_PROTOCOL,
            "status": "accepted",
            "runnerId": RUNNER_ID,
            "fingerprint": hashlib.sha256(decode_base64url(self.state.public_key)).hexdigest(),
            "requestBodySha256": hashlib.sha256(body).hexdigest(),
            "evidenceClass": "active_local_signing_key_possession",
        }
        response.update({field: False for field in RUNNER_PROBE_FALSE_ATTESTATIONS})
        self._json(200, response)

    def _json(self, status, value):
        self._raw_json(
            status,
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )

    def _raw_json(self, status, raw):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


@contextlib.contextmanager
def local_server():
    state = ServerState()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.agentwars_state = state
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def check_vector():
    print("[1] frozen Python/Nymrel signing vector")
    key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    material = public_key_material(key)
    signed = sign_runner_request(
        key,
        method="POST",
        path=RUNNER_PROBE_PATH,
        body=RUNNER_PROBE_BODY,
        runner_id="awr1_" + "A" * 22,
        timestamp="2026-08-25T12:00:00.000Z",
        nonce_bytes=bytes(range(16)),
    )
    check(material.public_key == "A6EHv_POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg", "public key vector")
    check(material.fingerprint == "56475aa75463474c0285df5dbf2bcab73da651358839e9b77481b2eab107708c", "fingerprint vector")
    check(signed.nonce == "AAECAwQFBgcICQoLDA0ODw", "nonce vector")
    check(signed.body_sha256 == "1aa3fcaa140a9ff20462c086d284d4afcadc4d1ddaf901da62ca02b414fd842f", "body digest vector")
    expected = (
        "agentwars.runner_request.v1\n"
        "method:POST\n"
        f"path:{RUNNER_PROBE_PATH}\n"
        "body-sha256:1aa3fcaa140a9ff20462c086d284d4afcadc4d1ddaf901da62ca02b414fd842f\n"
        "timestamp:2026-08-25T12:00:00.000Z\n"
        "nonce:AAECAwQFBgcICQoLDA0ODw\n"
        "runner-id:awr1_AAAAAAAAAAAAAAAAAAAAAA\n"
    )
    check(signed.canonical == expected, "canonical message exact")
    check(signed.canonical.endswith("\n") and not signed.canonical.endswith("\n\n"), "TypeScript join emits one trailing LF")
    check("\r" not in signed.canonical, "canonical message contains no CR")
    check(signed.signature == "FATK2J0R9j77xCut44eEfz7ovRcY7Xv1y6J2BgilIS65yh4LSX4zCUDz2UI2upX63PwNGf3PA1h9E6HKgzpDBA", "signature vector")
    key.public_key().verify(decode_base64url(signed.signature), signed.canonical.encode("utf-8"))
    check(set(signed.headers) == {
        "Content-Type", "agentwars-protocol", "agentwars-runner-id",
        "agentwars-timestamp", "agentwars-nonce", "agentwars-signature",
    }, "signed header exact set")
    check(signed.headers["agentwars-protocol"] == REQUEST_PROTOCOL, "request protocol header")


def check_origins_and_bodies():
    print("[2] origin, path, and body fail-closed policy")
    check(validate_origin("https://nymrel.com") == "https://nymrel.com", "production origin")
    for hostile in (
        "http://nymrel.com",
        "https://nymrel.com/",
        "https://NYMREL.COM",
        "https://nymrel.com:443",
        "https://nymrel.com.evil",
        "https://nymrel.com@evil.test",
        "https://nymrel.com?x=1",
        "https://nymrel.com#x",
        "http://localhost:8000",
        "http://127.1:8000",
        "http://127.0.0.1:8000/",
        "http://[::1%25eth0]:8000",
    ):
        expect_error(lambda hostile=hostile: validate_origin(hostile), RunnerClientError)
    check(validate_json_body(b'{"unicode":"\xc3\xa9"}') == b'{"unicode":"\xc3\xa9"}', "UTF-8 body preserved")
    for hostile in (b"", b"[]", b'{"a":1.5}', b'{"a":NaN}', b'{"a":1,"a":2}', b"not-json"):
        expect_error(lambda hostile=hostile: validate_json_body(hostile), RunnerClientError)
    canonical_fields = {
        "method": "POST",
        "path": "/api/builderwars/runners/probe",
        "body_sha256": "d" * 64,
        "timestamp": "2026-08-25T13:00:00.000Z",
        "nonce": "AAECAwQFBgcICQoLDA0ODw",
        "runner_id": "awr1_" + "A" * 22,
    }
    expect_error(
        lambda: canonical_runner_request(**{**canonical_fields, "timestamp": "2026-99-99T13:00:00.000Z"}),
        RunnerClientError,
    )
    expect_error(
        lambda: canonical_runner_request(**{**canonical_fields, "nonce": ("A" * 21) + "B"}),
        RunnerClientError,
    )
    for field, hostile, message_part in (
        ("method", "GET", "method"),
        ("path", "/api/probe?admin=1", "path"),
        ("path", "/api/probe\nrunner-id:awr1_fake", "path"),
        ("runner_id", "awr1_bad:runner", "runner id"),
    ):
        expect_error(
            lambda field=field, hostile=hostile: canonical_runner_request(
                **{**canonical_fields, field: hostile}
            ),
            RunnerClientError,
            message_part,
        )


def check_state_and_roundtrip():
    print("[3] encrypted key state, claim, activation, and signed HTTP roundtrip")
    with tempfile.TemporaryDirectory(prefix="agentwars-runner-check-") as temporary:
        state_dir = pathlib.Path(temporary) / "state"
        harness = pathlib.Path(temporary) / "harness.py"
        harness.write_bytes(b"print('runner')\n")
        harness_digest = digest_harness_file(harness)
        store = RunnerStateStore(state_dir)
        candidate = {
            "endpoint_origin": "http://127.0.0.1:1",
            "provider_id": "chatgpt_codex",
            "display_label": "Redraft Runner",
            "harness_id": "agentwars-cli",
            "harness_version": "1.0.0",
            "harness_digest": harness_digest,
        }
        profile, key, created = store.prepare(
            challenge_id=CHALLENGE_ID,
            passphrase=PASSPHRASE,
            **candidate,
        )
        check(created and profile["localState"] == "prepared", "new prepared profile")
        profile_again, key_again, created_again = store.prepare(
            challenge_id=CHALLENGE_ID,
            passphrase=PASSPHRASE,
            **candidate,
        )
        check(not created_again and profile_again["fingerprint"] == profile["fingerprint"], "retry reuses profile")
        check(public_key_material(key_again) == public_key_material(key), "retry reuses key")
        for field, changed, profile_field in (
            ("endpoint_origin", "http://127.0.0.1:2", "endpointOrigin"),
            ("provider_id", "claude_code", "providerId"),
            ("display_label", "Changed Runner", "displayLabel"),
            ("harness_id", "changed-harness", "harnessId"),
            ("harness_version", "2.0.0", "harnessVersion"),
            ("harness_digest", "f" * 64, "harnessDigest"),
        ):
            expect_error(
                lambda field=field, changed=changed: store.prepare(
                    challenge_id=CHALLENGE_ID,
                    passphrase=PASSPHRASE,
                    **{**candidate, field: changed},
                ),
                RunnerStateError,
                profile_field,
            )
        wrong_passphrase = b"wrong passphrase value"
        expect_error(
            lambda: store.load_key(profile, wrong_passphrase),
            RunnerStateError,
            "passphrase",
            forbid=(wrong_passphrase,),
        )
        key_bytes = store.key_path(CHALLENGE_ID).read_bytes()
        profile_bytes = store.profile_path(CHALLENGE_ID).read_bytes()
        check(b"ENCRYPTED PRIVATE KEY" in key_bytes, "PKCS8 key encrypted")
        for forbidden in (PAIRING_SECRET.encode(), PASSPHRASE):
            check(forbidden not in key_bytes and forbidden not in profile_bytes, "secret absent from state")
        check(profile["accountApprovalAttested"] is False, "account approval remains unattested locally")
        check(all(profile[field] is False for field in TRUST_FLAGS), "all trust flags false")

        with local_server() as (origin, server_state):
            # Bind this test profile to the actual loopback origin using a fresh challenge.
            second_id = "D" * 22
            second_secret = f"awp1_{second_id}_{'T' * 32}"
            second_profile, second_key, _ = store.prepare(
                challenge_id=second_id,
                passphrase=PASSPHRASE,
                endpoint_origin=origin,
                provider_id="chatgpt_codex",
                display_label="Dynasty Runner",
                harness_id="agentwars-cli",
                harness_version="1.0.0",
                harness_digest=harness_digest,
            )
            result = claim_runner(
                origin=origin,
                pairing_secret=second_secret,
                provider_id=second_profile["providerId"],
                display_label=second_profile["displayLabel"],
                harness_id=second_profile["harnessId"],
                harness_version=second_profile["harnessVersion"],
                harness_digest=second_profile["harnessDigest"],
                public_key=second_profile["publicKey"],
                fingerprint=second_profile["fingerprint"],
            )
            check(result.status == "claimed" and result.state == "pending_confirmation", "claim response accepted")
            request_capture = server_state.claim_requests[-1]
            check(second_secret not in request_capture["path"], "secret absent from URL")
            check(all(second_secret not in str(value) for value in request_capture["headers"].values()), "secret absent from headers")
            check(json.loads(request_capture["body"])["pairingSecret"] == second_secret, "secret only in exact POST body")
            second_profile = store.mark_claim_accepted(second_id, result.status)
            check(second_profile["localState"] == "pending_confirmation", "pending confirmation recorded")
            second_profile = store.record_runner_id(second_id, RUNNER_ID)
            check(second_profile["localState"] == "runner_id_recorded_unverified", "runner id remains locally unverified")
            check(
                all(second_profile[field] is False for field in TRUST_FLAGS),
                "trust flags stay false after state transitions",
            )
            signed = sign_runner_request(
                second_key,
                method="POST",
                path=RUNNER_PROBE_PATH,
                body=RUNNER_PROBE_BODY,
                runner_id=RUNNER_ID,
            )
            generated_nonces = {signed.nonce}
            for probe in range(2, 65):
                generated_nonces.add(
                    sign_runner_request(
                        second_key,
                        method="POST",
                        path=RUNNER_PROBE_PATH,
                        body=json.dumps({"probe": probe}, separators=(",", ":")).encode("utf-8"),
                        runner_id=RUNNER_ID,
                    ).nonce
                )
            check(len(generated_nonces) == 64, "generated request nonces are fresh across 64 signings")
            status, payload, _raw = send_signed_request(origin=origin, signed=signed)
            probe = validate_probe_response(
                payload,
                runner_id=RUNNER_ID,
                fingerprint=second_profile["fingerprint"],
                request_body_sha256=signed.body_sha256,
            )
            check(status == 200 and probe.runner_id == RUNNER_ID, "signed probe roundtrip")
            check(server_state.signed_requests[-1]["body"] == RUNNER_PROBE_BODY, "signed body bytes exact")
            expect_error(lambda: send_signed_request(origin=origin, signed=signed), RunnerHttpError, "HTTP 409")
            check(len(server_state.signed_requests) == 1, "replay not accepted")

            server_state.mode = "redirect"
            expect_error(
                lambda: claim_runner(
                    origin=origin,
                    pairing_secret=second_secret,
                    provider_id=second_profile["providerId"],
                    display_label=second_profile["displayLabel"],
                    harness_id=second_profile["harnessId"],
                    harness_version=second_profile["harnessVersion"],
                    harness_digest=second_profile["harnessDigest"],
                    public_key=second_profile["publicKey"],
                    fingerprint=second_profile["fingerprint"],
                ),
                RunnerHttpError,
                "redirect",
            )
            check(server_state.redirect_hits == 0, "redirect never receives secret")

            for mode, error_type, message_part in (
                ("mismatch", RunnerClientError, "fingerprint"),
                ("unknown_key", RunnerClientError, "response contract"),
                ("duplicate_key", RunnerClientError, "duplicate JSON keys"),
                ("wrong_status", RunnerClientError, "HTTP status contradicts"),
                ("non_json", RunnerHttpError, "non-JSON response"),
                ("oversize", RunnerHttpError, "response is too large"),
                ("chunked_oversize", RunnerHttpError, "response is too large"),
            ):
                server_state.mode = mode
                expect_error(
                    lambda: claim_runner(
                        origin=origin,
                        pairing_secret=second_secret,
                        provider_id=second_profile["providerId"],
                        display_label=second_profile["displayLabel"],
                        harness_id=second_profile["harnessId"],
                        harness_version=second_profile["harnessVersion"],
                        harness_digest=second_profile["harnessDigest"],
                        public_key=second_profile["publicKey"],
                        fingerprint=second_profile["fingerprint"],
                    ),
                    error_type,
                    message_part,
                    forbid=(second_secret,),
                )
            server_state.mode = "server_error"
            error = expect_error(
                lambda: claim_runner(
                    origin=origin,
                    pairing_secret=second_secret,
                    provider_id=second_profile["providerId"],
                    display_label=second_profile["displayLabel"],
                    harness_id=second_profile["harnessId"],
                    harness_version=second_profile["harnessVersion"],
                    harness_digest=second_profile["harnessDigest"],
                    public_key=second_profile["publicKey"],
                    fingerprint=second_profile["fingerprint"],
                ),
                RunnerHttpError,
            )
            check(second_secret not in str(error), "remote error cannot reflect secret")

            ambiguous_id = "A" * 22
            ambiguous_secret = f"awp1_{ambiguous_id}_{'U' * 32}"
            ambiguous_profile, _ambiguous_key, _ = store.prepare(
                challenge_id=ambiguous_id,
                passphrase=PASSPHRASE,
                endpoint_origin=origin,
                provider_id="chatgpt_codex",
                display_label="Ambiguous Runner",
                harness_id="agentwars-cli",
                harness_version="1.0.0",
                harness_digest=harness_digest,
            )
            server_state.mode = "drop_after_accept"
            expect_error(
                lambda: claim_runner(
                    origin=origin,
                    pairing_secret=ambiguous_secret,
                    provider_id=ambiguous_profile["providerId"],
                    display_label=ambiguous_profile["displayLabel"],
                    harness_id=ambiguous_profile["harnessId"],
                    harness_version=ambiguous_profile["harnessVersion"],
                    harness_digest=ambiguous_profile["harnessDigest"],
                    public_key=ambiguous_profile["publicKey"],
                    fingerprint=ambiguous_profile["fingerprint"],
                ),
                RunnerHttpError,
                "could not be reached",
                forbid=(ambiguous_secret,),
            )
            check(server_state.accepted_claims == 1, "server accepted claim before response connection dropped")

        ambiguous_profile = store.record_runner_id(ambiguous_id, RUNNER_ID)
        check(
            ambiguous_profile["localState"] == "runner_id_recorded_unverified",
            "owner can record a browser-issued id after an ambiguous claim response",
        )
        check(
            ambiguous_profile["serverClaimStatus"] == "not_confirmed",
            "ambiguous recovery preserves the missing local claim receipt",
        )

        tampered_id = "P" * 22
        tampered_profile, _tampered_key, _ = store.prepare(
            challenge_id=tampered_id,
            passphrase=PASSPHRASE,
            endpoint_origin="http://127.0.0.1:1",
            provider_id="chatgpt_codex",
            display_label="Tamper Probe",
            harness_id="agentwars-cli",
            harness_version="1.0.0",
            harness_digest=harness_digest,
        )
        tampered_profile["fingerprint"] = "0" * 64
        store.profile_path(tampered_id).write_bytes(
            (json.dumps(tampered_profile, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        )
        loaded_tampered_profile = store.load_profile(tampered_id)
        expect_error(
            lambda: store.load_key(loaded_tampered_profile, PASSPHRASE),
            RunnerStateError,
            "does not match",
            forbid=(PASSPHRASE,),
        )

        removed = store.forget(CHALLENGE_ID)
        check(removed["challengeId"] == CHALLENGE_ID, "forget returns public profile")
        check(not store.profile_path(CHALLENGE_ID).exists() and not store.key_path(CHALLENGE_ID).exists(), "forget removes exact local files")
        check(
            store.profile_path(second_id).exists() and store.key_path(second_id).exists(),
            "forget preserves sibling runner state",
        )

        linked_store = RunnerStateStore(pathlib.Path(temporary) / "linked-state")
        linked_root = linked_store.ensure()
        linked_target = pathlib.Path(temporary) / "must-not-change.txt"
        linked_target.write_bytes(b"protected")
        os.link(linked_target, linked_root / ".state.lock")
        expect_error(linked_store.list_profiles, RunnerStateError, "lock path is unsafe")
        check(linked_target.read_bytes() == b"protected", "hard-linked lock target is never modified")

        directory_lock_store = RunnerStateStore(pathlib.Path(temporary) / "directory-lock-state")
        (directory_lock_store.ensure() / ".state.lock").mkdir()
        expect_error(directory_lock_store.list_profiles, RunnerStateError, "lock could not be opened")

        dangling_root = pathlib.Path(temporary) / "dangling-state-root"
        try:
            dangling_root.symlink_to(pathlib.Path(temporary) / "missing-state-target", target_is_directory=True)
        except (NotImplementedError, OSError):
            print("SKIP: dangling-root symlink unavailable on this host")
        else:
            expect_error(RunnerStateStore(dangling_root).ensure, RunnerStateError, "must not be a symlink")

        dangling_key_store = RunnerStateStore(pathlib.Path(temporary) / "dangling-key-state")
        dangling_key_id = "K" * 22
        dangling_key_root = dangling_key_store.ensure()
        dangling_key_path = dangling_key_store.key_path(dangling_key_id)
        try:
            dangling_key_path.symlink_to(dangling_key_root / "missing-private-key.pem")
        except (NotImplementedError, OSError):
            print("SKIP: dangling-key symlink unavailable on this host")
        else:
            expect_error(
                lambda: dangling_key_store.prepare(
                    challenge_id=dangling_key_id,
                    passphrase=PASSPHRASE,
                    **candidate,
                ),
                RunnerStateError,
                "must not be a symlink",
            )

        forget_symlink_store = RunnerStateStore(pathlib.Path(temporary) / "forget-symlink-state")
        forget_symlink_id = "L" * 22
        forget_profile, _forget_key, _ = forget_symlink_store.prepare(
            challenge_id=forget_symlink_id,
            passphrase=PASSPHRASE,
            **candidate,
        )
        forget_key_path = forget_symlink_store.key_path(forget_symlink_id)
        forget_key_path.unlink()
        try:
            forget_key_path.symlink_to(forget_symlink_store.ensure() / "missing-after-prepare.pem")
        except (NotImplementedError, OSError):
            print("SKIP: forget dangling-key symlink unavailable on this host")
        else:
            removed = forget_symlink_store.forget(forget_symlink_id)
            check(removed["fingerprint"] == forget_profile["fingerprint"], "forget returns symlink-sabotaged profile")
            check(
                not forget_key_path.is_symlink()
                and not forget_symlink_store.profile_path(forget_symlink_id).exists(),
                "forget removes a dangling key link without following it",
            )


def check_claim_response_and_cli_argv():
    print("[4] exact response schema and no-secret argv diagnostics")
    base = {
        "schemaVersion": 1,
        "protocolVersion": "agentwars.runner_pairing.v1",
        "status": "claimed",
        "challengeId": CHALLENGE_ID,
        "state": "pending_confirmation",
        "fingerprint": "f" * 64,
    }
    check(validate_claim_response(base, challenge_id=CHALLENGE_ID, fingerprint="f" * 64).status == "claimed", "exact claim response")
    for hostile in (
        {**base, "extra": True},
        {**base, "schemaVersion": True},
        {**base, "schemaVersion": 1.0},
        {**base, "challengeId": "Z" * 22},
        {**base, "status": "Claimed"},
        {**base, "state": "active"},
        {**base, "fingerprint": "0" * 64},
        {**base, "fingerprint": "F" * 64},
    ):
        expect_error(
            lambda hostile=hostile: validate_claim_response(
                hostile, challenge_id=CHALLENGE_ID, fingerprint="f" * 64
            ),
            RunnerClientError,
        )

    probe_base = {
        "schemaVersion": 1,
        "protocolVersion": REQUEST_PROTOCOL,
        "status": "accepted",
        "runnerId": RUNNER_ID,
        "fingerprint": "f" * 64,
        "requestBodySha256": "d" * 64,
        "evidenceClass": "active_local_signing_key_possession",
        **{field: False for field in RUNNER_PROBE_FALSE_ATTESTATIONS},
    }
    result = validate_probe_response(
        probe_base,
        runner_id=RUNNER_ID,
        fingerprint="f" * 64,
        request_body_sha256="d" * 64,
    )
    check(result.runner_id == RUNNER_ID, "exact runner probe response")
    probe_hostiles = [
        {**probe_base, "extra": True},
        {key: value for key, value in probe_base.items() if key != "status"},
        {**probe_base, "schemaVersion": True},
        {**probe_base, "schemaVersion": 1.0},
        {**probe_base, "protocolVersion": PAIRING_CLAIM_PATH},
        {**probe_base, "status": "Accepted"},
        {**probe_base, "runnerId": "awr1_" + "Z" * 22},
        {**probe_base, "fingerprint": "0" * 64},
        {**probe_base, "requestBodySha256": "0" * 64},
        {**probe_base, "evidenceClass": "model_attested"},
        *({**probe_base, field: True} for field in RUNNER_PROBE_FALSE_ATTESTATIONS),
    ]
    for hostile in probe_hostiles:
        expect_error(
            lambda hostile=hostile: validate_probe_response(
                hostile,
                runner_id=RUNNER_ID,
                fingerprint="f" * 64,
                request_body_sha256="d" * 64,
            ),
            RunnerClientError,
        )
    process = subprocess.run(
        [sys.executable, os.path.join(ROOT, "bin", "agentwars.py"), "runner", "pair", PAIRING_SECRET],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )
    combined = process.stdout + process.stderr
    check(process.returncode == 2, "pairing secret argv refused")
    check(PAIRING_SECRET not in combined, "pairing secret absent from argv error output")
    check("no-echo prompt" in combined, "argv refusal points to hidden prompt")

    passphrase_marker = "never-echo-this-runner-passphrase"
    process = subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "bin", "agentwars.py"),
            "runner",
            "pair",
            "--passphrase",
            passphrase_marker,
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )
    combined = process.stdout + process.stderr
    check(process.returncode == 2, "passphrase argv refused")
    check(passphrase_marker not in combined, "passphrase absent from argv error output")
    check("no-echo prompt" in combined, "passphrase argv refusal points to hidden prompt")

    process = subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "bin", "agentwars.py"),
            "runner",
            "pair",
            f"--pas={passphrase_marker}",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )
    combined = process.stdout + process.stderr
    check(process.returncode == 2, "abbreviated passphrase argv refused")
    check(passphrase_marker not in combined, "passphrase absent from abbreviated argv error output")

    cli_path = os.path.join(ROOT, "bin", "agentwars.py")
    spec = importlib.util.spec_from_file_location("agentwars_cli_interrupt_test", cli_path)
    check(spec is not None and spec.loader is not None, "CLI module can be loaded for interrupt test")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    check(cli._bounded_timeout("60") == 60, "maximum bounded CLI timeout accepted")
    for hostile_timeout in ("0", "-1", "61", "not-an-integer"):
        expect_error(
            lambda hostile_timeout=hostile_timeout: cli._bounded_timeout(hostile_timeout),
            argparse.ArgumentTypeError,
            "1 to 60",
        )

    cli_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    cli_material = public_key_material(cli_key)
    cli_profile = {
        "localState": "runner_id_recorded_unverified",
        "runnerId": RUNNER_ID,
        "endpointOrigin": "https://nymrel.com",
        "fingerprint": cli_material.fingerprint,
    }

    class FakeSecret:
        @staticmethod
        def reveal():
            return PASSPHRASE

    class FakeStore:
        @staticmethod
        def load_profile(challenge_id):
            check(challenge_id == CHALLENGE_ID, "probe loads the exact challenge")
            return cli_profile

        @staticmethod
        def load_key(profile, passphrase):
            check(profile is cli_profile and passphrase == PASSPHRASE, "probe loads the exact encrypted key")
            return cli_key

    def accepted_probe(*, origin, signed, timeout_seconds):
        check(origin == "https://nymrel.com" and timeout_seconds == 15, "probe keeps origin and timeout")
        response = {
            "schemaVersion": 1,
            "protocolVersion": REQUEST_PROTOCOL,
            "status": "accepted",
            "runnerId": signed.runner_id,
            "fingerprint": cli_material.fingerprint,
            "requestBodySha256": signed.body_sha256,
            "evidenceClass": "active_local_signing_key_possession",
            **{field: False for field in RUNNER_PROBE_FALSE_ATTESTATIONS},
        }
        raw = json.dumps(response, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return 200, response, raw

    original_store = cli.RunnerStateStore
    original_existing_prompt = cli._existing_key_passphrase
    original_send_signed_request = cli.send_signed_request
    try:
        cli.RunnerStateStore = lambda _state_dir: FakeStore()
        cli._existing_key_passphrase = lambda: FakeSecret()
        cli.send_signed_request = accepted_probe
        probe_stdout = io.StringIO()
        with contextlib.redirect_stdout(probe_stdout):
            probe_status = cli.cmd_runner_probe(
                argparse.Namespace(challenge_id=CHALLENGE_ID, state_dir=None, timeout=15)
            )
        probe_output = probe_stdout.getvalue()
        check(probe_status == 0, "first-class probe command succeeds")
        check("exact active-key probe contract" in probe_output, "probe reports bounded success")
        check("attestations remain false" in probe_output, "probe reports trust boundary")
        check(PASSPHRASE.decode("utf-8") not in probe_output, "probe never prints the key passphrase")

        def overstated_probe(**kwargs):
            status, response, raw = accepted_probe(**kwargs)
            response = {**response, "modelAttested": True}
            return status, response, raw

        cli.send_signed_request = overstated_probe
        expect_error(
            lambda: cli.cmd_runner_probe(
                argparse.Namespace(challenge_id=CHALLENGE_ID, state_dir=None, timeout=15)
            ),
            RunnerClientError,
            "modelAttested",
        )
    finally:
        cli.RunnerStateStore = original_store
        cli._existing_key_passphrase = original_existing_prompt
        cli.send_signed_request = original_send_signed_request

    check(cli._looks_like_secret_option("--pas=value"), "abbreviated secret option recognized")
    check(not cli._looks_like_secret_option("--path"), "ordinary path option is not secret-shaped")
    original_hidden_prompt = cli._hidden_prompt
    cli._hidden_prompt = lambda _label: ""
    expect_error(cli._pairing_secret_prompt, RunnerClientError)
    cli._hidden_prompt = original_hidden_prompt

    environment_markers = {
        "AGENTWARS_PAIRING_SECRET": "awp1_" + ("E" * 22) + "_" + ("F" * 32),
        "AGENTWARS_PASSPHRASE": passphrase_marker,
        "AGENTWARS_KEY_PASSPHRASE": passphrase_marker,
    }
    previous_environment = {name: os.environ.get(name) for name in environment_markers}
    try:
        os.environ.update(environment_markers)

        def blocked_prompt(_label):
            raise RunnerClientError("prompt required despite environment")

        cli._hidden_prompt = blocked_prompt
        expect_error(cli._pairing_secret_prompt, RunnerClientError, "prompt required")
        expect_error(cli._existing_key_passphrase, RunnerClientError, "prompt required")
    finally:
        cli._hidden_prompt = original_hidden_prompt
        for name, previous in previous_environment.items():
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous

    with tempfile.TemporaryDirectory(prefix="agentwars-response-check-") as temporary:
        blocked_parent = pathlib.Path(temporary) / "not-a-directory"
        blocked_parent.write_bytes(b"occupied")
        expect_error(
            lambda: cli._write_response(str(blocked_parent / "response.json"), b"{}"),
            RunnerClientError,
            "output directory",
        )

        race_target = pathlib.Path(temporary) / "race-response.json"
        original_os_open = cli.os.open

        def concurrent_creator(path, flags, mode):
            winner = original_os_open(path, flags, mode)
            try:
                os.write(winner, b"winner")
            finally:
                os.close(winner)
            raise FileExistsError("simulated O_EXCL loser")

        cli.os.open = concurrent_creator
        try:
            expect_error(
                lambda: cli._write_response(str(race_target), b"loser"),
                RunnerClientError,
                "could not be written",
            )
        finally:
            cli.os.open = original_os_open
        check(race_target.read_bytes() == b"winner", "response race loser never deletes winner file")

        failed_write_target = pathlib.Path(temporary) / "failed-write-response.json"
        original_fdopen = cli.os.fdopen
        cli.os.fdopen = lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("simulated write failure"))
        try:
            expect_error(
                lambda: cli._write_response(str(failed_write_target), b"partial"),
                RunnerClientError,
                "could not be written",
            )
        finally:
            cli.os.fdopen = original_fdopen
        check(not failed_write_target.exists(), "failed response write removes only its own new file")

        class FailingWriter:
            def __init__(self, descriptor, error):
                self.descriptor = descriptor
                self.error = error

            def __enter__(self):
                return self

            def __exit__(self, _error_type, _error, _traceback):
                os.close(self.descriptor)

            def write(self, _raw):
                raise self.error

        partial_write_target = pathlib.Path(temporary) / "partial-write-response.json"
        cli.os.fdopen = lambda descriptor, *_args, **_kwargs: FailingWriter(
            descriptor, OSError("simulated ENOSPC")
        )
        try:
            expect_error(
                lambda: cli._write_response(str(partial_write_target), b"partial"),
                RunnerClientError,
                "could not be written",
            )
        finally:
            cli.os.fdopen = original_fdopen
        check(not partial_write_target.exists(), "partial response write removes its own truncated file")

        interrupted_write_target = pathlib.Path(temporary) / "interrupted-write-response.json"
        cli.os.fdopen = lambda descriptor, *_args, **_kwargs: FailingWriter(
            descriptor, KeyboardInterrupt()
        )
        try:
            expect_error(
                lambda: cli._write_response(str(interrupted_write_target), b"partial"),
                KeyboardInterrupt,
            )
        finally:
            cli.os.fdopen = original_fdopen
        check(not interrupted_write_target.exists(), "cancelled response write removes its own truncated file")

    class InterruptingParser:
        @staticmethod
        def parse_args(_argv):
            class Args:
                @staticmethod
                def func(_args):
                    raise KeyboardInterrupt

            return Args()

    cli.build_parser = lambda: InterruptingParser()
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        interrupt_status = cli.main([])
    interrupt_message = stderr.getvalue()
    check(interrupt_status == 130, "CLI interrupt returns the conventional status")
    check("encrypted local state may already exist" in interrupt_message, "interrupt warning preserves crash truth")
    check("no secret or passphrase was saved" not in interrupt_message, "interrupt warning makes no false no-write claim")


def main():
    faulthandler.dump_traceback_later(30, exit=True)
    try:
        check_vector()
        check_origins_and_bodies()
        check_state_and_roundtrip()
        check_claim_response_and_cli_argv()
        print(f"PASS: {CHECKS} AgentWars runner checks")
        print("provider/model/runtime/execution attestations remain false")
        return 0
    finally:
        faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    raise SystemExit(main())
