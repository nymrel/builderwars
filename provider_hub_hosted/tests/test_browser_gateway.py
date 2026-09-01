from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provider_hub.local_runner import base64url_no_pad, claim_payload, public_key_material
from provider_hub_hosted.browser_gateway import (
    BROWSER_GATEWAY_EVIDENCE_CLASS,
    BROWSER_GATEWAY_SCHEMA,
    MAX_BROWSER_BODY_BYTES,
    PRODUCTION_AUTHORITY,
    BrowserAuthenticationError,
    BrowserAuthorizationGateway,
    BrowserRequest,
    IdempotencyResponseKeyring,
    InMemoryAccountRateLimiter,
    VerifiedBrowserPrincipal,
)
from provider_hub_hosted.handlers import HostedControlPlane
from provider_hub_hosted.store import HostedControlPlaneStore


UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)
BROWSER_ORIGIN = "https://builderwars.example"
ISSUER = "https://clerk.builderwars.example"
CSRF = base64url_no_pad(b"c" * 32)
IDEMPOTENCY_RESPONSE_KEY = b"i" * 32
IDEMPOTENCY_RESPONSE_KEYRING = IdempotencyResponseKeyring(
    active_key_id="local-current",
    keys={"local-current": IDEMPOTENCY_RESPONSE_KEY},
)


class DeterministicBytes:
    def __init__(self):
        self.counter = 0

    def __call__(self, size: int) -> bytes:
        self.counter += 1
        return hashlib.sha512(f"browser-gateway-{self.counter}".encode("ascii")).digest()[:size]


def principal(subject: str = "user_alpha", session_id: str = "session_alpha", **overrides):
    values = {
        "issuer": ISSUER,
        "subject": subject,
        "session_id": session_id,
        "verified_at": NOW,
    }
    values.update(overrides)
    return VerifiedBrowserPrincipal(**values)


class BrowserGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="builderwars-browser-auth-")
        self.database = Path(self.temporary.name) / "hosted.sqlite3"
        self.random = DeterministicBytes()
        self.request_counter = 0
        self.store = HostedControlPlaneStore(self.database, random_bytes=self.random, clock=lambda: NOW)
        self.control = HostedControlPlane(self.store, allowed_origin="https://nymrel.com")
        self.limiter = InMemoryAccountRateLimiter()
        self.gateway = BrowserAuthorizationGateway(
            self.control,
            allowed_origin=BROWSER_ORIGIN,
            expected_issuer=ISSUER,
            owner_pepper=b"synthetic-owner-pepper-not-a-production-secret-0001",
            idempotency_response_keyring=IDEMPOTENCY_RESPONSE_KEYRING,
            rate_limiter=self.limiter,
        )

    def tearDown(self):
        self.store.close()
        self.temporary.cleanup()

    def request(
        self,
        path: str,
        *,
        method: str = "POST",
        body: bytes = b"{}",
        origin: str = BROWSER_ORIGIN,
        content_type: str | None = "application/json",
        csrf_cookie: str = CSRF,
        csrf_header: str = CSRF,
        idempotency_key: str | None = None,
    ) -> BrowserRequest:
        if idempotency_key is None:
            self.request_counter += 1
            material = hashlib.sha256(f"browser-request-{self.request_counter}".encode("ascii")).digest()[:16]
            idempotency_key = "awi1_" + base64url_no_pad(material)
        return BrowserRequest(
            method=method,
            path=path,
            body=body,
            origin=origin,
            content_type=content_type,
            csrf_cookie=csrf_cookie,
            csrf_header=csrf_header,
            idempotency_key=idempotency_key,
        )

    def dispatch(self, request: BrowserRequest, *, who=None, now=NOW):
        who = who or principal()
        return self.gateway.dispatch(request, resolve_principal=lambda: who, now=now)

    def owner(self, who=None) -> str:
        return self.gateway.owner_id_for(who or principal(), now=NOW)

    def pair_direct(self, who=None):
        who = who or principal()
        owner = self.owner(who)
        created = self.control.create_pairing(owner, now=NOW)
        key = Ed25519PrivateKey.generate()
        material = public_key_material(key)
        body = json.dumps(
            claim_payload(
                pairing_secret=created.payload["pairingSecret"],
                provider_id="chatgpt_codex",
                display_label="Browser Gateway Test",
                harness_id="agentwars-fixture",
                harness_version="1.0.0",
                harness_digest="4" * 64,
                public_key=material.public_key,
            ),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.control.claim_pairing(body, now=NOW)
        confirmed = self.control.confirm_pairing(
            owner,
            created.payload["challengeId"],
            approved=True,
            now=NOW,
        )
        return owner, confirmed.payload["runnerId"], created.payload["challengeId"]

    def assert_error(self, response, status: int, code: str):
        self.assertEqual(response.status_code, status)
        self.assertEqual(
            response.payload,
            {"schemaVersion": 1, "status": "error", "error": {"code": code}},
        )

    def test_contract_is_explicitly_local_and_non_authoritative(self):
        contract = self.gateway.contract()
        self.assertEqual(contract["schemaVersion"], BROWSER_GATEWAY_SCHEMA)
        self.assertEqual(contract["evidenceClass"], BROWSER_GATEWAY_EVIDENCE_CLASS)
        self.assertEqual(contract["maxBodyBytes"], MAX_BROWSER_BODY_BYTES)
        self.assertEqual(contract["idempotencyKeyBytes"], 16)
        self.assertEqual(contract["idempotencyTtlSeconds"], 86_400)
        self.assertEqual(
            contract["idempotencyResponseProtection"],
            "aes256gcm_authenticated_encryption",
        )
        self.assertEqual(
            contract["idempotencyResponseEnvelopeSchema"],
            "agentwars.idempotency_response_envelope/1",
        )
        self.assertEqual(contract["idempotencyResponseKeyringMaxKeys"], 3)
        self.assertEqual(
            contract["idempotencyResponseKeyIdBytes"],
            {"min": 3, "max": 32},
        )
        self.assertEqual(
            contract["idempotencyAtomicity"],
            "same_sqlite_transaction_local_reference",
        )
        self.assertFalse(contract["requestCarriesAuthenticationMaterial"])
        self.assertFalse(contract["requestAcceptsOwnerId"])
        self.assertEqual(contract["productionAuthority"], PRODUCTION_AUTHORITY)
        self.assertTrue(all(value is False for value in contract["productionAuthority"].values()))
        self.assertNotIn("subject", json.dumps(contract))
        self.assertNotIn("session_alpha", json.dumps(contract))

    def test_owner_is_opaque_stable_and_domain_separated(self):
        first = self.owner(principal("user_alpha"))
        repeated = self.owner(principal("user_alpha", "session_other"))
        second = self.owner(principal("user_beta"))
        other_gateway = BrowserAuthorizationGateway(
            self.control,
            allowed_origin=BROWSER_ORIGIN,
            expected_issuer=ISSUER,
            owner_pepper=b"different-synthetic-owner-pepper-value-0000001",
            idempotency_response_keyring=IDEMPOTENCY_RESPONSE_KEYRING,
            rate_limiter=InMemoryAccountRateLimiter(),
        )
        other_pepper = other_gateway.owner_id_for(principal("user_alpha"), now=NOW)
        self.assertEqual(first, repeated)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, other_pepper)
        self.assertRegex(first, r"^awu1_[A-Za-z0-9_-]{22}$")
        self.assertNotIn("user", first)
        self.assertNotIn("user_alpha", repr(principal("user_alpha", "session_secret")))
        self.assertNotIn("session_secret", repr(principal("user_alpha", "session_secret")))
        self.assertNotIn("synthetic-owner-pepper", repr(self.gateway))

    def test_create_pairing_uses_derived_owner_and_returns_no_principal(self):
        response = self.dispatch(self.request("/v1/browser/pairings"))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.payload["schemaVersion"], 1)
        self.assertIn("challengeId", response.payload)
        self.assertIn("pairingSecret", response.payload)
        rendered = json.dumps(response.payload, sort_keys=True)
        self.assertNotIn("user_alpha", rendered)
        self.assertNotIn("session_alpha", rendered)
        self.assertNotIn("ownerId", rendered)
        self.assertEqual(response.headers["RateLimit-Limit"], "6")

    def test_preflight_refuses_before_resolving_principal(self):
        hostile = (
            self.request("/v1/browser/pairings", origin="https://evil.example"),
            self.request("/v1/browser/pairings", csrf_header=base64url_no_pad(b"x" * 32)),
            self.request("/v1/browser/pairings", csrf_cookie="not-canonical"),
            self.request("/v1/browser/pairings", content_type="text/plain"),
            self.request("/v1/browser/pairings?ownerId=awu1_fake"),
            self.request("//v1/browser/pairings"),
            self.request("/v1/browser/pairings", body=b"x" * (MAX_BROWSER_BODY_BYTES + 1)),
        )
        for request in hostile:
            calls = 0

            def should_not_run():
                nonlocal calls
                calls += 1
                raise AssertionError("principal resolver crossed failed preflight")

            response = self.gateway.dispatch(request, resolve_principal=should_not_run, now=NOW)
            self.assertIn(response.status_code, {403, 404, 413, 415})
            self.assertEqual(calls, 0)

    def test_origin_is_one_exact_canonical_value(self):
        for bad in (
            "https://builderwars.example/",
            "https://BUILDERWARS.example",
            "http://builderwars.example",
            "https://builderwars.example:443",
            "https://builderwars.example.evil.test",
            "https://user@builderwars.example",
            "https://builderwärs.example",
        ):
            response = self.dispatch(self.request("/v1/browser/pairings", origin=bad))
            self.assert_error(response, 403, "forbidden")

    def test_principal_failures_are_uniform_and_safe(self):
        requests = self.request("/v1/browser/pairings")
        failures = (
            object(),
            principal(issuer="https://other-issuer.example"),
            principal(subject="bad subject"),
            principal(session_id="bad session"),
            principal(authentication_class="unverified_claims"),
            principal(verified_at=NOW - dt.timedelta(seconds=301)),
            principal(verified_at=NOW + dt.timedelta(seconds=31)),
            principal(verified_at=NOW.replace(tzinfo=None)),
        )
        for who in failures:
            response = self.gateway.dispatch(requests, resolve_principal=lambda who=who: who, now=NOW)
            self.assert_error(response, 401, "authentication_required")
        expected = self.gateway.dispatch(
            requests,
            resolve_principal=lambda: (_ for _ in ()).throw(BrowserAuthenticationError("token detail")),
            now=NOW,
        )
        self.assert_error(expected, 401, "authentication_required")
        unavailable = self.gateway.dispatch(
            requests,
            resolve_principal=lambda: (_ for _ in ()).throw(RuntimeError("backend detail")),
            now=NOW,
        )
        self.assert_error(unavailable, 503, "authentication_unavailable")
        self.assertNotIn("detail", json.dumps(expected.payload) + json.dumps(unavailable.payload))

    def test_body_schemas_refuse_owner_injection_duplicates_floats_and_invalid_utf8(self):
        hostile = (
            b'{"ownerId":"awu1_AAAAAAAAAAAAAAAAAAAAAA"}',
            b'{"approved":true,"approved":false}',
            b'{"approved":1}',
            b'{"approved":1.0}',
            b'{"approved":NaN}',
            b"\xff",
            b"[]",
            b"",
        )
        for body in hostile:
            path = "/v1/browser/pairings/AAAAAAAAAAAAAAAAAAAAAA/confirm"
            response = self.dispatch(self.request(path, body=body))
            self.assert_error(response, 400, "invalid_request")

    def test_route_method_and_identifier_confusion_fail_closed(self):
        cases = (
            self.request("/v1/browser/pairings", method="DELETE", body=b"", content_type=None),
            self.request("/v1/browser/account"),
            self.request("/v1/browser/account", method="DELETE", body=b"{}", content_type=None),
            self.request("/v1/browser/runners/awr1_bad/revoke"),
            self.request("/v1/browser/runners/awr1_AAAAAAAAAAAAAAAAAAAAAA%2Frevoke"),
            self.request("/v1/browser/unknown"),
        )
        expected = (404, 404, 400, 404, 404, 404)
        for request, status in zip(cases, expected, strict=True):
            response = self.dispatch(request)
            self.assert_error(response, status, "invalid_request" if status == 400 else "not_found")

    def test_pairing_confirmation_is_tenant_scoped_and_foreign_probe_is_uniform(self):
        alpha = principal("user_alpha", "session_alpha")
        beta = principal("user_beta", "session_beta")
        owner, _runner, challenge = self.pair_direct(alpha)
        self.assertEqual(owner, self.owner(alpha))
        body = b'{"approved":true}'
        foreign = self.dispatch(
            self.request(f"/v1/browser/pairings/{challenge}/confirm", body=body),
            who=beta,
        )
        self.assert_error(foreign, 404, "not_found")
        repeated = self.dispatch(
            self.request(f"/v1/browser/pairings/{challenge}/confirm", body=body),
            who=alpha,
        )
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.payload["state"], "active")

    def test_runner_fixture_revoke_delete_and_account_delete_routes(self):
        who = principal()
        owner, runner, _challenge = self.pair_direct(who)
        fixture = self.dispatch(
            self.request(
                f"/v1/browser/runners/{runner}/fixture-jobs",
                body=json.dumps({"seed": base64url_no_pad(b"s" * 16)}, separators=(",", ":")).encode("ascii"),
            ),
            who=who,
        )
        self.assertEqual((fixture.status_code, fixture.payload["status"]), (201, "queued"))
        self.assertFalse(fixture.payload["modelAttested"])
        self.assertFalse(fixture.payload["matchExecutionAttested"])
        revoked = self.dispatch(
            self.request(f"/v1/browser/runners/{runner}/revoke"),
            who=who,
        )
        self.assertEqual((revoked.status_code, revoked.payload["status"]), (200, "revoked"))
        deleted = self.dispatch(
            self.request(
                f"/v1/browser/runners/{runner}",
                method="DELETE",
                body=b"",
                content_type=None,
            ),
            who=who,
        )
        self.assertEqual((deleted.status_code, deleted.payload["status"]), (200, "deleted"))
        account = self.dispatch(
            self.request("/v1/browser/account", method="DELETE", body=b"", content_type=None),
            who=who,
        )
        self.assertEqual(account.status_code, 200)
        self.assertEqual(account.payload["ownerId"], owner)

    def test_fixture_schema_refuses_owner_and_unsafe_seed(self):
        _owner, runner, _challenge = self.pair_direct()
        for body in (
            b'{"ownerId":"awu1_AAAAAAAAAAAAAAAAAAAAAA"}',
            b'{"seed":"../../secret"}',
            b'{"seed":"ok","extra":true}',
            b'{"seed":1}',
        ):
            response = self.dispatch(
                self.request(f"/v1/browser/runners/{runner}/fixture-jobs", body=body)
            )
            self.assert_error(response, 400, "invalid_request")

    def test_account_rate_limit_is_owner_and_operation_scoped(self):
        path = "/v1/browser/pairings"
        alpha = [self.dispatch(self.request(path), who=principal("user_alpha")) for _ in range(7)]
        self.assertEqual([row.status_code for row in alpha[:6]], [201] * 6)
        self.assert_error(alpha[6], 429, "rate_limited")
        self.assertEqual(alpha[6].headers["Retry-After"], "60")
        beta = self.dispatch(self.request(path), who=principal("user_beta", "session_beta"))
        self.assertEqual(beta.status_code, 201)
        delete_account = self.dispatch(
            self.request("/v1/browser/account", method="DELETE", body=b"", content_type=None),
            who=principal("user_alpha"),
        )
        self.assertEqual(delete_account.status_code, 200)

    def test_rate_limit_reference_is_atomic_under_concurrency(self):
        limiter = InMemoryAccountRateLimiter()
        owner = self.owner()
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            decisions = list(
                executor.map(
                    lambda _index: limiter.check(owner, "create_pairing", now=NOW),
                    range(24),
                )
            )
        self.assertEqual(sum(decision.allowed for decision in decisions), 6)
        self.assertEqual(sum(not decision.allowed for decision in decisions), 18)
        self.assertTrue(all(decision.limit == 6 for decision in decisions))

    def test_rate_limit_window_resets_without_claiming_durability(self):
        path = "/v1/browser/pairings"
        who = principal()
        for _ in range(6):
            self.assertEqual(self.dispatch(self.request(path), who=who, now=NOW).status_code, 201)
        limited = self.dispatch(self.request(path), who=who, now=NOW)
        self.assertEqual(limited.status_code, 429)
        reset = self.dispatch(self.request(path), who=who, now=NOW + dt.timedelta(seconds=60))
        self.assertEqual(reset.status_code, 201)
        self.assertEqual(self.gateway.contract()["rateLimiterBoundary"], "injected_owner_scoped_fail_closed")
        self.assertEqual(self.gateway.contract()["localRateLimiterReference"], "in_memory_account_fixed_window")
        self.assertFalse(self.gateway.contract()["productionAuthority"]["durableAccountRateLimitsActive"])

    def test_rate_limiter_failure_or_malformed_decision_fails_closed(self):
        class BrokenLimiter:
            def check(self, owner_id, operation, *, now):
                del owner_id, operation, now
                raise RuntimeError("redis detail")

        class MalformedLimiter:
            def check(self, owner_id, operation, *, now):
                del owner_id, operation, now
                return {"allowed": True}

        for limiter in (BrokenLimiter(), MalformedLimiter()):
            gateway = BrowserAuthorizationGateway(
                self.control,
                allowed_origin=BROWSER_ORIGIN,
                expected_issuer=ISSUER,
                owner_pepper=b"synthetic-owner-pepper-not-a-production-secret-0001",
                idempotency_response_keyring=IDEMPOTENCY_RESPONSE_KEYRING,
                rate_limiter=limiter,
            )
            response = gateway.dispatch(
                self.request("/v1/browser/pairings"),
                resolve_principal=lambda: principal(),
                now=NOW,
            )
            self.assert_error(response, 503, "rate_limit_unavailable")
            self.assertNotIn("redis", json.dumps(response.payload))

    def test_constructor_refuses_weak_or_malformed_security_configuration(self):
        for bad_origin in ("http://builderwars.example", "https://builderwars.example/", "https://user@builderwars.example"):
            with self.assertRaises(ValueError):
                BrowserAuthorizationGateway(
                    self.control,
                    allowed_origin=bad_origin,
                    expected_issuer=ISSUER,
                    owner_pepper=b"x" * 32,
                    idempotency_response_keyring=IDEMPOTENCY_RESPONSE_KEYRING,
                    rate_limiter=InMemoryAccountRateLimiter(),
                )
        with self.assertRaises(ValueError):
            BrowserAuthorizationGateway(
                self.control,
                allowed_origin=BROWSER_ORIGIN,
                expected_issuer=ISSUER,
                owner_pepper=b"weak",
                idempotency_response_keyring=IDEMPOTENCY_RESPONSE_KEYRING,
                rate_limiter=InMemoryAccountRateLimiter(),
            )
        with self.assertRaises(TypeError):
            BrowserAuthorizationGateway(
                self.control,
                allowed_origin=BROWSER_ORIGIN,
                expected_issuer=ISSUER,
                owner_pepper=b"x" * 32,
                idempotency_response_keyring=b"weak",
                rate_limiter=InMemoryAccountRateLimiter(),
            )
        with self.assertRaises(ValueError):
            InMemoryAccountRateLimiter({"create_pairing": (1, 60)})


if __name__ == "__main__":
    unittest.main()
