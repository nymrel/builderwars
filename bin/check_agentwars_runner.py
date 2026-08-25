#!/usr/bin/env python3
"""Hostile local checks for AgentWars runner pairing and request signing.

No provider is contacted.  HTTP exercises a literal 127.0.0.1 test server;
all state lives in a temporary directory and is removed on exit.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import http.server
import importlib.util
import io
import json
import os
import pathlib
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
)
from provider_hub.runner_state import RunnerStateError, RunnerStateStore  # noqa: E402


CHECKS = 0
RUNNER_ID = "awr1_" + "R" * 22
CHALLENGE_ID = "C" * 22
PAIRING_SECRET = f"awp1_{CHALLENGE_ID}_{'S' * 32}"
PASSPHRASE = b"correct horse battery staple"


def check(condition, label):
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def expect_error(action, error_type, message_part=None):
    try:
        action()
    except error_type as error:
        if message_part is not None:
            check(message_part in str(error), f"error contains {message_part!r}")
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
        if self.path == "/api/builderwars/runners/probe":
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
        request = json.loads(body.decode("utf-8"))
        challenge_id, _random_code = parse_pairing_secret(request["pairingSecret"])
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
        self._json(200, {"ok": True, "runnerId": RUNNER_ID})

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
        path="/api/builderwars/runners/probe",
        body=b'{"a":1}',
        runner_id="awr1_" + "A" * 22,
        timestamp="2026-08-25T13:00:00.000Z",
        nonce_bytes=bytes(range(16)),
    )
    check(material.public_key == "A6EHv_POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg", "public key vector")
    check(material.fingerprint == "56475aa75463474c0285df5dbf2bcab73da651358839e9b77481b2eab107708c", "fingerprint vector")
    check(signed.nonce == "AAECAwQFBgcICQoLDA0ODw", "nonce vector")
    check(signed.body_sha256 == "015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862", "body digest vector")
    expected = (
        "agentwars.runner_request.v1\n"
        "method:POST\n"
        "path:/api/builderwars/runners/probe\n"
        "body-sha256:015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862\n"
        "timestamp:2026-08-25T13:00:00.000Z\n"
        "nonce:AAECAwQFBgcICQoLDA0ODw\n"
        "runner-id:awr1_AAAAAAAAAAAAAAAAAAAAAA\n"
    )
    check(signed.canonical == expected, "canonical message exact")
    check(signed.canonical.endswith("\n") and not signed.canonical.endswith("\n\n"), "TypeScript join emits one trailing LF")
    check("\r" not in signed.canonical, "canonical message contains no CR")
    check(signed.signature == "YoZI7mmg43q04TUyutiQvQgusUhS_9NsrC-tdnH6KKLUZaL5XaFgCBLri_Y5aTnxTd7EIPm8BMPgfnUV6d4HCA", "signature vector")
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


def check_state_and_roundtrip():
    print("[3] encrypted key state, claim, activation, and signed HTTP roundtrip")
    with tempfile.TemporaryDirectory(prefix="agentwars-runner-check-") as temporary:
        state_dir = pathlib.Path(temporary) / "state"
        harness = pathlib.Path(temporary) / "harness.py"
        harness.write_bytes(b"print('runner')\n")
        harness_digest = digest_harness_file(harness)
        store = RunnerStateStore(state_dir)
        profile, key, created = store.prepare(
            challenge_id=CHALLENGE_ID,
            passphrase=PASSPHRASE,
            endpoint_origin="http://127.0.0.1:1",
            provider_id="chatgpt_codex",
            display_label="Redraft Runner",
            harness_id="agentwars-cli",
            harness_version="1.0.0",
            harness_digest=harness_digest,
        )
        check(created and profile["localState"] == "prepared", "new prepared profile")
        profile_again, key_again, created_again = store.prepare(
            challenge_id=CHALLENGE_ID,
            passphrase=PASSPHRASE,
            endpoint_origin="http://127.0.0.1:1",
            provider_id="chatgpt_codex",
            display_label="Redraft Runner",
            harness_id="agentwars-cli",
            harness_version="1.0.0",
            harness_digest=harness_digest,
        )
        check(not created_again and profile_again["fingerprint"] == profile["fingerprint"], "retry reuses profile")
        check(public_key_material(key_again) == public_key_material(key), "retry reuses key")
        expect_error(
            lambda: store.prepare(
                challenge_id=CHALLENGE_ID,
                passphrase=PASSPHRASE,
                endpoint_origin="http://127.0.0.1:1",
                provider_id="chatgpt_codex",
                display_label="Changed Runner",
                harness_id="agentwars-cli",
                harness_version="1.0.0",
                harness_digest=harness_digest,
            ),
            RunnerStateError,
            "metadata drift",
        )
        expect_error(lambda: store.load_key(profile, b"wrong passphrase value"), RunnerStateError)
        key_bytes = store.key_path(CHALLENGE_ID).read_bytes()
        profile_bytes = store.profile_path(CHALLENGE_ID).read_bytes()
        check(b"ENCRYPTED PRIVATE KEY" in key_bytes, "PKCS8 key encrypted")
        for forbidden in (PAIRING_SECRET.encode(), PASSPHRASE):
            check(forbidden not in key_bytes and forbidden not in profile_bytes, "secret absent from state")
        check(profile["accountApprovalAttested"] is False, "account approval remains unattested locally")
        check(all(profile[field] is False for field in (
            "providerAccountAttested", "planEntitlementAttested", "billingRouteAttested",
            "modelAttested", "personAttested", "runtimeAttested",
            "harnessExecutionAttested", "matchExecutionAttested",
        )), "all trust flags false")

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
            signed = sign_runner_request(
                second_key,
                method="POST",
                path="/api/builderwars/runners/probe",
                body=b'{"probe":1}',
                runner_id=RUNNER_ID,
            )
            status, payload, _raw = send_signed_request(origin=origin, signed=signed)
            check(status == 200 and payload == {"ok": True, "runnerId": RUNNER_ID}, "signed request roundtrip")
            check(server_state.signed_requests[-1]["body"] == b'{"probe":1}', "signed body bytes exact")
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

            for mode, error_type in (
                ("mismatch", RunnerClientError),
                ("unknown_key", RunnerClientError),
                ("duplicate_key", RunnerClientError),
                ("wrong_status", RunnerClientError),
                ("non_json", RunnerHttpError),
                ("oversize", RunnerHttpError),
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

        ambiguous_profile = store.record_runner_id(CHALLENGE_ID, RUNNER_ID)
        check(
            ambiguous_profile["localState"] == "runner_id_recorded_unverified",
            "owner can record a browser-issued id after an ambiguous claim response",
        )
        check(
            ambiguous_profile["serverClaimStatus"] == "not_confirmed",
            "ambiguous recovery preserves the missing local claim receipt",
        )

        removed = store.forget(CHALLENGE_ID)
        check(removed["challengeId"] == CHALLENGE_ID, "forget returns public profile")
        check(not store.profile_path(CHALLENGE_ID).exists() and not store.key_path(CHALLENGE_ID).exists(), "forget removes exact local files")


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
        {**base, "state": "active"},
        {**base, "fingerprint": "0" * 64},
    ):
        expect_error(
            lambda hostile=hostile: validate_claim_response(
                hostile, challenge_id=CHALLENGE_ID, fingerprint="f" * 64
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

    cli_path = os.path.join(ROOT, "bin", "agentwars.py")
    spec = importlib.util.spec_from_file_location("agentwars_cli_interrupt_test", cli_path)
    check(spec is not None and spec.loader is not None, "CLI module can be loaded for interrupt test")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

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
    check_vector()
    check_origins_and_bodies()
    check_state_and_roundtrip()
    check_claim_response_and_cli_argv()
    print(f"PASS: {CHECKS} AgentWars runner checks")
    print("provider/model/runtime/execution attestations remain false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
