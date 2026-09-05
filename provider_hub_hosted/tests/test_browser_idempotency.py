from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path

from provider_hub.local_runner import base64url_no_pad
from provider_hub_hosted.browser_gateway import (
    IDEMPOTENCY_RESPONSE_ENVELOPE_MAGIC,
    BrowserAuthorizationGateway,
    BrowserRequest,
    IdempotencyResponseKeyring,
    InMemoryAccountRateLimiter,
    VerifiedBrowserPrincipal,
)
from provider_hub_hosted.handlers import HostedControlPlane
from provider_hub_hosted.store import (
    BROWSER_IDEMPOTENCY_TTL_SECONDS,
    HostedControlPlaneStore,
    HostedStoreError,
)


UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)
BROWSER_ORIGIN = "https://builderwars.example"
ISSUER = "https://clerk.builderwars.example"
CSRF = base64url_no_pad(b"c" * 32)
OWNER_PEPPER = b"synthetic-owner-pepper-not-a-production-secret-0001"
RESPONSE_KEY = b"i" * 32


class DeterministicBytes:
    def __init__(self):
        self.counter = 0
        self.lock = threading.Lock()

    def __call__(self, size: int) -> bytes:
        with self.lock:
            self.counter += 1
            counter = self.counter
        return hashlib.sha512(f"browser-idempotency-{counter}".encode("ascii")).digest()[:size]


class FailAfterMutationGateway(BrowserAuthorizationGateway):
    """Test seam proving a post-domain-mutation failure rolls back everything."""

    def _invoke_and_seal(self, operation: str, **kwargs):
        self._invoke(
            operation,
            owner_id=kwargs["owner_id"],
            parameters=kwargs["parameters"],
            payload=kwargs["payload"],
            now=kwargs["now"],
        )
        raise RuntimeError("synthetic failure after domain mutation")


def principal(
    subject: str = "user_alpha",
    *,
    verified_at: dt.datetime = NOW,
) -> VerifiedBrowserPrincipal:
    return VerifiedBrowserPrincipal(
        issuer=ISSUER,
        subject=subject,
        session_id=f"session_{subject}",
        verified_at=verified_at,
    )


def idempotency_key(label: str) -> str:
    material = hashlib.sha256(label.encode("ascii")).digest()[:16]
    return "awi1_" + base64url_no_pad(material)


class BrowserIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="builderwars-browser-idempotency-")
        self.database = Path(self.temporary.name) / "hosted.sqlite3"
        self.random = DeterministicBytes()
        self.store = HostedControlPlaneStore(
            self.database,
            random_bytes=self.random,
            clock=lambda: NOW,
        )
        self.gateway = self._gateway(self.store)

    def tearDown(self):
        self.store.close()
        self.temporary.cleanup()

    @staticmethod
    def _gateway(
        store: HostedControlPlaneStore,
        *,
        response_key: bytes = RESPONSE_KEY,
        keyring: IdempotencyResponseKeyring | None = None,
        gateway_type=BrowserAuthorizationGateway,
    ) -> BrowserAuthorizationGateway:
        return gateway_type(
            HostedControlPlane(store, allowed_origin="https://nymrel.com"),
            allowed_origin=BROWSER_ORIGIN,
            expected_issuer=ISSUER,
            owner_pepper=OWNER_PEPPER,
            idempotency_response_keyring=keyring or IdempotencyResponseKeyring(
                active_key_id="local-current",
                keys={"local-current": response_key},
            ),
            rate_limiter=InMemoryAccountRateLimiter(),
        )

    @staticmethod
    def _request(
        key: str,
        *,
        path: str = "/v1/browser/pairings",
        method: str = "POST",
        body: bytes = b"{}",
    ) -> BrowserRequest:
        return BrowserRequest(
            method=method,
            path=path,
            body=body,
            origin=BROWSER_ORIGIN,
            content_type="application/json",
            csrf_cookie=CSRF,
            csrf_header=CSRF,
            idempotency_key=key,
        )

    def _dispatch(
        self,
        request: BrowserRequest,
        *,
        who: VerifiedBrowserPrincipal | None = None,
        now: dt.datetime = NOW,
        gateway: BrowserAuthorizationGateway | None = None,
    ):
        return (gateway or self.gateway).dispatch(
            request,
            resolve_principal=lambda: who or principal(),
            now=now,
        )

    def _count(self, table: str) -> int:
        if table not in {"owners", "pairing_challenges", "browser_idempotency"}:
            raise ValueError("unsupported test table")
        with self.store._lock:
            row = self.store._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])

    def assert_error(self, response, status: int, code: str):
        self.assertEqual(response.status_code, status)
        self.assertEqual(
            response.payload,
            {"schemaVersion": 1, "status": "error", "error": {"code": code}},
        )

    def test_invalid_key_is_refused_before_authentication(self):
        resolver_calls = 0

        def resolve():
            nonlocal resolver_calls
            resolver_calls += 1
            return principal()

        for key in ("", "awi1_short", "awi1_!!!!!!!!!!!!!!!!!!!!!!"):
            response = self.gateway.dispatch(self._request(key), resolve_principal=resolve, now=NOW)
            self.assert_error(response, 400, "invalid_request")
        self.assertEqual(resolver_calls, 0)
        self.assertEqual(self._count("pairing_challenges"), 0)

    def test_response_keyring_rejects_invalid_bounds_ids_material_and_duplicates(self):
        valid = IdempotencyResponseKeyring(
            active_key_id="key-current",
            keys={"key-current": b"a" * 32},
        )
        self.assertEqual(valid.active_key_id, "key-current")
        self.assertEqual(valid.key_ids, ("key-current",))
        self.assertNotIn((b"a" * 32).hex(), repr(valid))
        with self.assertRaises(AttributeError):
            valid.active_key_id = "key-replaced"  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            valid.key_ids = ("key-replaced",)  # type: ignore[misc]

        invalid = (
            {"active_key_id": "key-current", "keys": {}},
            {"active_key_id": "key-missing", "keys": {"key-current": b"a" * 32}},
            {
                "active_key_id": "key-a",
                "keys": {
                    "key-a": b"a" * 32,
                    "key-b": b"b" * 32,
                    "key-c": b"c" * 32,
                    "key-d": b"d" * 32,
                },
            },
            {"active_key_id": "UPPERCASE", "keys": {"UPPERCASE": b"a" * 32}},
            {"active_key_id": "key-current", "keys": {"key-current": b"weak"}},
            {
                "active_key_id": "key-a",
                "keys": {"key-a": b"a" * 32, "key-b": b"a" * 32},
            },
        )
        for values in invalid:
            with self.subTest(values=tuple(values["keys"])):
                with self.assertRaises((TypeError, ValueError)):
                    IdempotencyResponseKeyring(**values)

        with self.assertRaises(TypeError):
            IdempotencyResponseKeyring(active_key_id="key-current", keys=[])  # type: ignore[arg-type]

    def test_same_owner_key_and_request_replays_exact_pairing_response(self):
        request = self._request(idempotency_key("exact-replay"))
        first = self._dispatch(request)
        replay = self._dispatch(request)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(first.payload, replay.payload)
        self.assertEqual(first.headers["Idempotency-Replayed"], "false")
        self.assertEqual(replay.headers["Idempotency-Replayed"], "true")
        self.assertEqual(first.headers["Idempotency-Expires-At"], replay.headers["Idempotency-Expires-At"])
        self.assertEqual(self._count("pairing_challenges"), 1)
        self.assertEqual(self._count("browser_idempotency"), 1)

        secret = first.payload["pairingSecret"].encode("ascii")
        with self.store._lock:
            sealed = self.store._connection.execute(
                "SELECT sealed_response FROM browser_idempotency"
            ).fetchone()[0]
        self.assertIs(type(sealed), bytes)
        self.assertNotIn(secret, sealed)
        self.assertNotIn(first.payload["pairingSecret"], repr(self.gateway))
        self.assertNotIn(request.idempotency_key, repr(request))

    def test_same_owner_key_with_different_request_conflicts_without_mutation(self):
        key = idempotency_key("request-conflict")
        first = self._dispatch(self._request(key, body=b"{}"))
        conflict = self._dispatch(self._request(key, body=b"{ }"))

        self.assertEqual(first.status_code, 201)
        self.assert_error(conflict, 409, "idempotency_conflict")
        self.assertEqual(self._count("pairing_challenges"), 1)
        self.assertEqual(self._count("browser_idempotency"), 1)

    def test_same_key_is_isolated_between_owners(self):
        request = self._request(idempotency_key("owner-isolation"))
        first = self._dispatch(request, who=principal("user_alpha"))
        second = self._dispatch(request, who=principal("user_beta"))

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.payload["challengeId"], second.payload["challengeId"])
        self.assertNotEqual(first.payload["pairingSecret"], second.payload["pairingSecret"])
        self.assertEqual(self._count("pairing_challenges"), 2)
        self.assertEqual(self._count("browser_idempotency"), 2)

    def test_six_concurrent_retries_commit_one_mutation_and_one_response(self):
        request = self._request(idempotency_key("concurrent-retries"))
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            responses = list(executor.map(lambda _index: self._dispatch(request), range(6)))

        self.assertEqual({response.status_code for response in responses}, {201})
        payloads = {json.dumps(response.payload, sort_keys=True) for response in responses}
        self.assertEqual(len(payloads), 1)
        replay_flags = [response.headers["Idempotency-Replayed"] for response in responses]
        self.assertEqual(replay_flags.count("false"), 1)
        self.assertEqual(replay_flags.count("true"), 5)
        self.assertEqual(self._count("pairing_challenges"), 1)
        self.assertEqual(self._count("browser_idempotency"), 1)

    def test_two_store_connections_race_to_one_mutation_and_response(self):
        other_store = HostedControlPlaneStore(
            self.database,
            random_bytes=DeterministicBytes(),
            clock=lambda: NOW,
        )
        other_gateway = self._gateway(other_store)
        request = self._request(idempotency_key("two-store-race"))
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(self._dispatch, request, gateway=gateway)
                    for gateway in (self.gateway, other_gateway)
                ]
                responses = [future.result() for future in futures]
        finally:
            other_store.close()

        self.assertEqual({response.status_code for response in responses}, {201})
        self.assertEqual(responses[0].payload, responses[1].payload)
        self.assertEqual(
            sorted(response.headers["Idempotency-Replayed"] for response in responses),
            ["false", "true"],
        )
        self.assertEqual(self._count("pairing_challenges"), 1)
        self.assertEqual(self._count("browser_idempotency"), 1)

    def test_store_rejects_short_sealed_response_and_rolls_back_record(self):
        owner_id = self.gateway.owner_id_for(principal(), now=NOW)
        with self.assertRaises(HostedStoreError) as raised:
            self.store.run_browser_mutation_idempotent(
                owner_id,
                idempotency_key("short-sealed-response"),
                "create_pairing",
                "a" * 64,
                execute=lambda: (201, b"x" * 27),
                now=NOW,
            )
        self.assertEqual(raised.exception.code, "invalid_idempotency_response")
        self.assertEqual(self._count("browser_idempotency"), 0)

    def test_post_mutation_failure_rolls_back_domain_and_idempotency_rows(self):
        failing = self._gateway(self.store, gateway_type=FailAfterMutationGateway)
        response = self._dispatch(
            self._request(idempotency_key("post-mutation-failure")),
            gateway=failing,
        )

        self.assert_error(response, 503, "idempotency_unavailable")
        self.assertEqual(self._count("owners"), 0)
        self.assertEqual(self._count("pairing_challenges"), 0)
        self.assertEqual(self._count("browser_idempotency"), 0)

    def test_replay_survives_store_and_gateway_restart_with_same_key(self):
        request = self._request(idempotency_key("restart-replay"))
        first = self._dispatch(request)
        self.store.close()
        self.store = HostedControlPlaneStore(
            self.database,
            random_bytes=self.random,
            clock=lambda: NOW,
        )
        restarted = self._gateway(self.store)
        replay = self._dispatch(request, gateway=restarted)

        self.assertEqual(first.payload, replay.payload)
        self.assertEqual(replay.headers["Idempotency-Replayed"], "true")
        self.assertEqual(self._count("pairing_challenges"), 1)

    def test_staged_key_rotation_replays_retiring_key_and_seals_new_active_key(self):
        old_ring = IdempotencyResponseKeyring(
            active_key_id="key-2026-a",
            keys={"key-2026-a": b"a" * 32},
        )
        old_gateway = self._gateway(self.store, keyring=old_ring)
        old_request = self._request(idempotency_key("before-key-rotation"))
        original = self._dispatch(old_request, gateway=old_gateway)

        overlap_ring = IdempotencyResponseKeyring(
            active_key_id="key-2026-b",
            keys={"key-2026-a": b"a" * 32, "key-2026-b": b"b" * 32},
        )
        overlap_gateway = self._gateway(self.store, keyring=overlap_ring)
        old_replay = self._dispatch(old_request, gateway=overlap_gateway)
        new_request = self._request(idempotency_key("after-key-rotation"))
        new_response = self._dispatch(new_request, gateway=overlap_gateway)

        self.assertEqual(original.payload, old_replay.payload)
        self.assertEqual(old_replay.headers["Idempotency-Replayed"], "true")
        self.assertEqual(new_response.status_code, 201)
        self.assertEqual(new_response.headers["Idempotency-Replayed"], "false")
        with self.store._lock:
            rows = self.store._connection.execute(
                "SELECT idempotency_key, sealed_response FROM browser_idempotency"
            ).fetchall()
        envelope_ids = {}
        for row in rows:
            sealed = row["sealed_response"]
            self.assertTrue(sealed.startswith(IDEMPOTENCY_RESPONSE_ENVELOPE_MAGIC))
            key_id_length = sealed[len(IDEMPOTENCY_RESPONSE_ENVELOPE_MAGIC)]
            start = len(IDEMPOTENCY_RESPONSE_ENVELOPE_MAGIC) + 1
            envelope_ids[row["idempotency_key"]] = sealed[start:start + key_id_length].decode("ascii")
        self.assertEqual(envelope_ids[old_request.idempotency_key], "key-2026-a")
        self.assertEqual(envelope_ids[new_request.idempotency_key], "key-2026-b")

        retired_ring = IdempotencyResponseKeyring(
            active_key_id="key-2026-b",
            keys={"key-2026-b": b"b" * 32},
        )
        retired_gateway = self._gateway(self.store, keyring=retired_ring)
        old_refused = self._dispatch(old_request, gateway=retired_gateway)
        new_replay = self._dispatch(new_request, gateway=retired_gateway)
        self.assert_error(old_refused, 503, "idempotency_unavailable")
        self.assertEqual(new_replay.payload, new_response.payload)
        self.assertEqual(new_replay.headers["Idempotency-Replayed"], "true")
        self.assertEqual(self._count("pairing_challenges"), 2)

    def test_key_id_substitution_fails_even_when_both_keys_are_available(self):
        ring = IdempotencyResponseKeyring(
            active_key_id="key-a",
            keys={"key-a": b"a" * 32, "key-b": b"b" * 32},
        )
        gateway = self._gateway(self.store, keyring=ring)
        request = self._request(idempotency_key("key-id-substitution"))
        first = self._dispatch(request, gateway=gateway)
        with self.store._transaction() as connection:
            sealed = connection.execute(
                "SELECT sealed_response FROM browser_idempotency"
            ).fetchone()[0]
            key_id_length_offset = len(IDEMPOTENCY_RESPONSE_ENVELOPE_MAGIC)
            key_id_length = sealed[key_id_length_offset]
            key_id_start = key_id_length_offset + 1
            self.assertEqual(sealed[key_id_start:key_id_start + key_id_length], b"key-a")
            substituted = (
                sealed[:key_id_start]
                + b"key-b"
                + sealed[key_id_start + key_id_length:]
            )
            connection.execute(
                "UPDATE browser_idempotency SET sealed_response = ?",
                (substituted,),
            )
        refused = self._dispatch(request, gateway=gateway)

        self.assertEqual(first.status_code, 201)
        self.assert_error(refused, 503, "idempotency_unavailable")
        self.assertEqual(self._count("pairing_challenges"), 1)

    def test_wrong_response_key_fails_closed_without_second_mutation(self):
        request = self._request(idempotency_key("wrong-response-key"))
        first = self._dispatch(request)
        wrong_key_gateway = self._gateway(self.store, response_key=b"w" * 32)
        refused = self._dispatch(request, gateway=wrong_key_gateway)

        self.assertEqual(first.status_code, 201)
        self.assert_error(refused, 503, "idempotency_unavailable")
        self.assertEqual(self._count("pairing_challenges"), 1)

    def test_tampered_ciphertext_fails_closed_without_second_mutation(self):
        request = self._request(idempotency_key("tampered-response"))
        first = self._dispatch(request)
        with self.store._transaction() as connection:
            connection.execute(
                "UPDATE browser_idempotency SET sealed_response = zeroblob(length(sealed_response))"
            )
        refused = self._dispatch(request)

        self.assertEqual(first.status_code, 201)
        self.assert_error(refused, 503, "idempotency_unavailable")
        self.assertEqual(self._count("pairing_challenges"), 1)

    def test_expired_record_allows_one_fresh_mutation(self):
        request = self._request(idempotency_key("expired-record"))
        first = self._dispatch(request)
        later = NOW + dt.timedelta(seconds=BROWSER_IDEMPOTENCY_TTL_SECONDS + 1)
        fresh = self._dispatch(request, now=later, who=principal(verified_at=later))

        self.assertEqual(first.status_code, 201)
        self.assertEqual(fresh.status_code, 201)
        self.assertEqual(fresh.headers["Idempotency-Replayed"], "false")
        self.assertNotEqual(first.payload["challengeId"], fresh.payload["challengeId"])
        self.assertEqual(self._count("pairing_challenges"), 2)
        self.assertEqual(self._count("browser_idempotency"), 1)

    def test_account_delete_response_remains_replayable_for_retry_window(self):
        create = self._dispatch(self._request(idempotency_key("delete-setup")))
        owner_id = self.gateway.owner_id_for(principal(), now=NOW)
        request = self._request(
            idempotency_key("delete-replay"),
            path="/v1/browser/account",
            method="DELETE",
            body=b"",
        )
        first = self._dispatch(request)
        replay = self._dispatch(request)

        self.assertEqual(create.status_code, 201)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.payload, replay.payload)
        self.assertEqual(first.payload["ownerId"], owner_id)
        self.assertEqual(replay.headers["Idempotency-Replayed"], "true")
        self.assertEqual(self._count("owners"), 0)
        self.assertEqual(self._count("pairing_challenges"), 0)
        self.assertEqual(self._count("browser_idempotency"), 2)


if __name__ == "__main__":
    unittest.main()
