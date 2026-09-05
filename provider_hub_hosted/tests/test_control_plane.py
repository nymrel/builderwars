from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provider_hub.local_runner import (
    REQUEST_PROTOCOL,
    RUNNER_PROBE_BODY,
    RUNNER_PROBE_PATH,
    base64url_no_pad,
    canonical_instant,
    canonical_runner_request,
    claim_payload,
    public_key_material,
    sign_runner_request,
    validate_claim_response,
    validate_probe_response,
)
from provider_hub.match_worker import (
    MATCH_JOB_ABANDON_PATH,
    MATCH_JOB_ENGINE_SHA256,
    MATCH_JOB_MAX_ATTEMPTS,
    MATCH_JOB_POLL_BODY,
    MATCH_JOB_POLL_PATH,
    MATCH_JOB_RENEW_PATH,
    MATCH_JOB_RESULT_PATH,
    FixtureGrant,
    FixturePollTerminal,
    compute_closed_fixture,
    encode_result_request,
    fixture_transcript_sha256,
    validate_poll_response,
    validate_result_response,
)
from provider_hub_hosted.handlers import HostedControlPlane
from provider_hub_hosted.store import (
    MAX_REQUEST_AGE_SECONDS,
    MAX_REQUEST_FUTURE_SECONDS,
    HostedControlPlaneStore,
    HostedStoreError,
)
from provider_hub_hosted.verify import (
    IncomingSignedRequest,
    SignedRequestError,
    verify_signed_request,
)


UTC = dt.timezone.utc
START = dt.datetime(2026, 8, 26, 10, 0, 0, tzinfo=UTC)


class DeterministicBytes:
    def __init__(self):
        self.counter = 0

    def __call__(self, size: int) -> bytes:
        self.counter += 1
        material = hashlib.sha512(f"agentwars-test-{self.counter}".encode("ascii")).digest()
        return material[:size]


class MutableClock:
    def __init__(self, current: dt.datetime):
        self.current = current

    def __call__(self) -> dt.datetime:
        return self.current


class CommitFailsOnceConnection:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.rollback_calls = 0
        self.should_fail = True

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def commit(self):
        if self.should_fail:
            self.should_fail = False
            raise sqlite3.OperationalError("injected commit failure")
        return self.connection.commit()

    def rollback(self):
        self.rollback_calls += 1
        return self.connection.rollback()


def owner_id(byte: int) -> str:
    return "awu1_" + base64url_no_pad(bytes([byte]) * 16)


class HostedControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="agentwars-hosted-test-")
        self.database = Path(self.temporary.name) / "control-plane.sqlite3"
        self.random = DeterministicBytes()
        self.now = START
        self.clock = MutableClock(self.now)
        self.origin = "https://nymrel.com"
        self.store = HostedControlPlaneStore(
            self.database,
            random_bytes=self.random,
            clock=self.clock,
        )
        self.control = HostedControlPlane(self.store, allowed_origin=self.origin)
        self.owner = owner_id(1)
        self.other_owner = owner_id(2)
        self.nonce_counter = 0

    def tearDown(self):
        self.store.close()
        self.temporary.cleanup()

    def pairing_body(self, secret, key, *, label="Sunday Machine"):
        payload = claim_payload(
            pairing_secret=secret,
            provider_id="chatgpt_codex",
            display_label=label,
            harness_id="agentwars-fixture",
            harness_version="1.0.0",
            harness_digest="4" * 64,
            public_key=public_key_material(key).public_key,
        )
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def pair(self, *, owner=None, label="Sunday Machine", now=None, key=None):
        owner = owner or self.owner
        now = now or self.now
        created = self.control.create_pairing(owner, now=now)
        secret = created.payload["pairingSecret"]
        challenge_id = created.payload["challengeId"]
        key = key or Ed25519PrivateKey.generate()
        material = public_key_material(key)
        body = self.pairing_body(secret, key, label=label)
        claimed = self.control.claim_pairing(body, now=now)
        validated = validate_claim_response(
            dict(claimed.payload), challenge_id=challenge_id, fingerprint=material.fingerprint
        )
        self.assertEqual(validated.status, "claimed")
        duplicate = self.control.claim_pairing(body, now=now)
        self.assertEqual((duplicate.status_code, duplicate.payload["status"]), (200, "duplicate"))
        confirmed = self.control.confirm_pairing(owner, challenge_id, approved=True, now=now)
        runner_id = confirmed.payload["runnerId"]
        profile = {
            "runnerId": runner_id,
            "fingerprint": material.fingerprint,
            "harnessId": "agentwars-fixture",
            "harnessDigest": "4" * 64,
        }
        return {
            "owner": owner,
            "key": key,
            "material": material,
            "secret": secret,
            "challenge_id": challenge_id,
            "runner_id": runner_id,
            "profile": profile,
        }

    def signed(
        self,
        paired,
        *,
        path,
        body,
        now=None,
        method="POST",
        key=None,
        runner_id=None,
        origin=None,
        protocol_version=REQUEST_PROTOCOL,
        nonce_bytes=None,
        advance_clock=True,
    ):
        now = now or self.now
        if advance_clock:
            self.clock.current = now
        if nonce_bytes is None:
            self.nonce_counter += 1
            nonce_bytes = self.nonce_counter.to_bytes(16, "big")
        signed = sign_runner_request(
            key or paired["key"],
            origin=origin or self.origin,
            method=method,
            path=path,
            body=body,
            runner_id=runner_id or paired["runner_id"],
            timestamp=canonical_instant(now),
            nonce_bytes=nonce_bytes,
        )
        return IncomingSignedRequest(
            method=signed.method,
            path=signed.path,
            body=signed.body,
            protocol_version=protocol_version,
            runner_id=signed.runner_id,
            timestamp=signed.timestamp,
            nonce=signed.nonce,
            signature=signed.signature,
        )

    def manual_signed(self, paired, *, path, body, now=None):
        now = now or self.now
        self.clock.current = now
        self.nonce_counter += 1
        nonce = base64url_no_pad(self.nonce_counter.to_bytes(16, "big"))
        stamp = canonical_instant(now)
        body_sha256 = hashlib.sha256(body).hexdigest()
        canonical = canonical_runner_request(
            origin=self.origin,
            method="POST",
            path=path,
            body_sha256=body_sha256,
            timestamp=stamp,
            nonce=nonce,
            runner_id=paired["runner_id"],
        )
        signature = base64url_no_pad(paired["key"].sign(canonical.encode("utf-8")))
        return IncomingSignedRequest(
            method="POST",
            path=path,
            body=body,
            protocol_version=REQUEST_PROTOCOL,
            runner_id=paired["runner_id"],
            timestamp=stamp,
            nonce=nonce,
            signature=signature,
        )

    def complete_job(self, paired, owner, *, now):
        self.clock.current = now
        self.control.create_fixture_job(owner, paired["runner_id"], now=now)
        polled = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY, now=now),
            now=now,
        )
        grant = validate_poll_response(
            dict(polled.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        self.assertIsInstance(grant, FixtureGrant)
        computation = compute_closed_fixture(grant)
        body = encode_result_request(grant, computation)
        self.control.result(
            self.signed(paired, path=MATCH_JOB_RESULT_PATH, body=body, now=now),
            now=now,
        )
        return grant

    def test_injected_clock_is_used_when_now_is_omitted(self):
        observed = self.now + dt.timedelta(days=2, milliseconds=123)
        self.clock.current = observed

        created = self.control.create_pairing(self.owner)

        expected_expiry = observed + dt.timedelta(seconds=600)
        self.assertEqual(created.payload["expiresAt"], canonical_instant(expected_expiry))
        inspection = sqlite3.connect(self.database)
        try:
            stored_created_at_ms = inspection.execute(
                "SELECT created_at_ms FROM pairing_challenges WHERE challenge_id = ?",
                (created.payload["challengeId"],),
            ).fetchone()[0]
        finally:
            inspection.close()
        self.assertEqual(stored_created_at_ms, int(observed.timestamp() * 1000))

    def test_noncanonical_owner_id_is_rejected_without_persistence(self):
        canonical = owner_id(3)
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        final_index = alphabet.index(canonical[-1])
        self.assertEqual(final_index % 4, 0)
        noncanonical = canonical[:-1] + alphabet[final_index + 1]

        with self.assertRaises(HostedStoreError) as refused:
            self.control.create_pairing(noncanonical, now=self.now)

        self.assertEqual(refused.exception.code, "invalid_owner")
        self.assertEqual(self.store.row_counts()["owners"], 0)
        self.assertEqual(self.store.row_counts()["pairing_challenges"], 0)

    def test_commit_failure_rolls_back_and_connection_remains_usable(self):
        failing = CommitFailsOnceConnection(self.store._connection)
        self.store._connection = failing

        with self.assertRaisesRegex(sqlite3.OperationalError, "injected commit failure"):
            self.control.create_pairing(self.owner, now=self.now)

        self.assertEqual(failing.rollback_calls, 1)
        self.assertEqual(self.store.row_counts()["owners"], 0)
        self.assertEqual(self.store.row_counts()["pairing_challenges"], 0)
        created = self.control.create_pairing(self.owner, now=self.now)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.store.row_counts()["pairing_challenges"], 1)

    def test_full_pair_probe_job_result_projection_and_delete(self):
        paired = self.pair()
        probe_request = self.signed(paired, path=RUNNER_PROBE_PATH, body=RUNNER_PROBE_BODY)
        probe = self.control.probe(probe_request, now=self.now)
        validated_probe = validate_probe_response(
            dict(probe.payload),
            runner_id=paired["runner_id"],
            fingerprint=paired["material"].fingerprint,
            request_body_sha256=hashlib.sha256(RUNNER_PROBE_BODY).hexdigest(),
        )
        self.assertEqual(validated_probe.evidence_class, "active_local_signing_key_possession")
        with self.assertRaisesRegex(SignedRequestError, "already used") as replayed:
            self.control.probe(probe_request, now=self.now)
        self.assertEqual(replayed.exception.code, "replayed_request")

        created_job = self.control.create_fixture_job(
            self.owner, paired["runner_id"], seed=base64url_no_pad(b"s" * 16), now=self.now
        )
        self.assertEqual(created_job.payload["status"], "queued")
        poll_request = self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY)
        polled = self.control.poll(poll_request, now=self.now)
        grant = validate_poll_response(
            dict(polled.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        self.assertIsInstance(grant, FixtureGrant)

        renew_body = json.dumps({
            "jobId": grant.job.job_id,
            "attemptId": grant.attempt_id,
            "leaseEpoch": grant.lease_epoch,
        }, separators=(",", ":")).encode("ascii")
        renewed = self.control.renew(
            self.signed(paired, path=MATCH_JOB_RENEW_PATH, body=renew_body), now=self.now
        )
        self.assertEqual((renewed.payload["status"], renewed.payload["attempt"]["renewCount"]), ("renewed", 1))

        computation = compute_closed_fixture(grant)
        result_body = encode_result_request(grant, computation)
        result_request = self.signed(paired, path=MATCH_JOB_RESULT_PATH, body=result_body)
        recorded = self.control.result(result_request, now=self.now)
        receipt = validate_result_response(
            dict(recorded.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(result_body).hexdigest(),
            grant=grant,
            computation=computation,
        )
        self.assertFalse(receipt.duplicate)
        duplicate = self.control.result(
            self.signed(paired, path=MATCH_JOB_RESULT_PATH, body=result_body), now=self.now
        )
        self.assertTrue(duplicate.payload["duplicate"])

        terminal = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY), now=self.now
        )
        terminal_value = validate_poll_response(
            dict(terminal.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        self.assertIsInstance(terminal_value, FixturePollTerminal)
        self.assertEqual(terminal_value.status, "completed")

        public = self.control.public_replay(grant.job.job_id)
        self.assertEqual(public.status_code, 200)
        serialized = json.dumps(public.payload, sort_keys=True)
        for forbidden in (
            "ownerId", "runnerId", "displayLabel", "providerId", "connectionMode",
            "harnessId", "harnessDigest", "seed", "pairingSecret", "nonce", "signature",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(public.payload["modelAttested"])
        self.assertFalse(public.payload["matchExecutionAttested"])

        deleted = self.control.delete_owner(self.owner)
        self.assertEqual(deleted.payload["status"], "deleted")
        self.assertEqual(self.control.public_replay(grant.job.job_id).status_code, 404)
        self.assertTrue(all(count == 0 for count in self.store.row_counts().values()))

    def test_pairing_secret_is_hash_only_expires_and_rate_locks(self):
        created = self.control.create_pairing(self.owner, now=self.now)
        secret = created.payload["pairingSecret"]
        challenge_id = created.payload["challengeId"]
        key = Ed25519PrivateKey.generate()
        material = public_key_material(key)
        for index in range(8):
            wrong_code = base64url_no_pad(bytes([index + 10]) * 24)
            wrong_secret = f"awp1_{challenge_id}_{wrong_code}"
            payload = claim_payload(
                pairing_secret=wrong_secret,
                provider_id="chatgpt_codex",
                display_label="Wrong",
                harness_id="agentwars-fixture",
                harness_version="1.0.0",
                harness_digest="4" * 64,
                public_key=material.public_key,
            )
            with self.assertRaises(HostedStoreError) as refused:
                self.control.claim_pairing(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(), now=self.now
                )
            self.assertEqual(refused.exception.code, "pairing_refused")
        correct = claim_payload(
            pairing_secret=secret,
            provider_id="chatgpt_codex",
            display_label="Correct",
            harness_id="agentwars-fixture",
            harness_version="1.0.0",
            harness_digest="4" * 64,
            public_key=material.public_key,
        )
        with self.assertRaises(HostedStoreError) as locked:
            self.control.claim_pairing(
                json.dumps(correct, sort_keys=True, separators=(",", ":")).encode(), now=self.now
            )
        self.assertEqual(locked.exception.code, "pairing_refused")

        self.store.close()
        database_bytes = b"".join(
            path.read_bytes() for path in self.database.parent.glob(self.database.name + "*") if path.is_file()
        )
        self.assertNotIn(secret.encode("ascii"), database_bytes)
        self.store = HostedControlPlaneStore(
            self.database,
            random_bytes=self.random,
            clock=self.clock,
        )
        self.control = HostedControlPlane(self.store, allowed_origin=self.origin)

        expiring = self.control.create_pairing(self.other_owner, now=self.now)
        expiring_key = Ed25519PrivateKey.generate()
        expiring_payload = claim_payload(
            pairing_secret=expiring.payload["pairingSecret"],
            provider_id="chatgpt_codex",
            display_label="Late",
            harness_id="agentwars-fixture",
            harness_version="1.0.0",
            harness_digest="4" * 64,
            public_key=public_key_material(expiring_key).public_key,
        )
        late = self.now + dt.timedelta(seconds=601)
        with self.assertRaises(HostedStoreError) as expired:
            self.control.claim_pairing(
                json.dumps(expiring_payload, sort_keys=True, separators=(",", ":")).encode(), now=late
            )
        self.assertEqual(expired.exception.code, "pairing_expired")
        with self.assertRaises(HostedStoreError) as still_expired:
            self.control.claim_pairing(
                json.dumps(expiring_payload, sort_keys=True, separators=(",", ":")).encode(), now=late
            )
        self.assertEqual(still_expired.exception.code, "pairing_refused")

    def test_concurrent_distinct_pairing_claims_have_one_winner(self):
        created = self.control.create_pairing(self.owner, now=self.now)
        keys = [Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()]
        bodies = [
            self.pairing_body(created.payload["pairingSecret"], key, label=f"Racer {index}")
            for index, key in enumerate(keys)
        ]

        def submit(body):
            try:
                return self.control.claim_pairing(body, now=self.now).payload["status"]
            except HostedStoreError as error:
                return error.code

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = sorted(executor.map(submit, bodies))
        self.assertEqual(outcomes, ["claimed", "pairing_conflict"])
        confirmed = self.control.confirm_pairing(
            self.owner, created.payload["challengeId"], approved=True, now=self.now
        )
        runner = self.store.get_runner(confirmed.payload["runnerId"], owner_id=self.owner)
        self.assertIn(runner.public_key, {public_key_material(key).public_key for key in keys})

    def test_pairing_rejection_confirmation_idempotency_and_key_reuse(self):
        rejected = self.control.create_pairing(self.owner, now=self.now)
        rejected_key = Ed25519PrivateKey.generate()
        self.control.claim_pairing(
            self.pairing_body(rejected.payload["pairingSecret"], rejected_key, label="Rejected"),
            now=self.now,
        )
        first = self.control.confirm_pairing(
            self.owner, rejected.payload["challengeId"], approved=False, now=self.now
        )
        second = self.control.confirm_pairing(
            self.owner, rejected.payload["challengeId"], approved=False, now=self.now
        )
        self.assertEqual((first.payload["state"], second.payload["state"]), ("rejected", "rejected"))
        with self.assertRaises(HostedStoreError) as reversed_decision:
            self.control.confirm_pairing(
                self.owner, rejected.payload["challengeId"], approved=True, now=self.now
            )
        self.assertEqual(reversed_decision.exception.code, "pairing_rejected")

        reusable_key = Ed25519PrivateKey.generate()
        paired = self.pair(key=reusable_key)
        repeated = self.control.confirm_pairing(
            self.owner, paired["challenge_id"], approved=True, now=self.now
        )
        self.assertEqual(repeated.payload["runnerId"], paired["runner_id"])

        duplicate_key = self.control.create_pairing(self.other_owner, now=self.now)
        self.control.claim_pairing(
            self.pairing_body(
                duplicate_key.payload["pairingSecret"], reusable_key, label="Cross-owner reuse"
            ),
            now=self.now,
        )
        with self.assertRaises(HostedStoreError) as key_reused:
            self.control.confirm_pairing(
                self.other_owner,
                duplicate_key.payload["challengeId"],
                approved=True,
                now=self.now,
            )
        self.assertEqual(key_reused.exception.code, "pairing_key_reused")

    def test_pairing_confirmation_is_tenant_scoped_and_wrong_owner_is_non_mutating(self):
        created = self.control.create_pairing(self.owner, now=self.now)
        key = Ed25519PrivateKey.generate()
        self.control.claim_pairing(
            self.pairing_body(created.payload["pairingSecret"], key, label="Tenant bound"),
            now=self.now,
        )
        before_counts = self.store.row_counts()

        for approved in (True, False):
            with self.assertRaises(HostedStoreError) as refused:
                self.control.confirm_pairing(
                    self.other_owner,
                    created.payload["challengeId"],
                    approved=approved,
                    now=self.now,
                )
            self.assertEqual(refused.exception.code, "not_found")
            self.assertEqual(self.store.row_counts(), before_counts)

        inspection = sqlite3.connect(self.database)
        try:
            state = inspection.execute(
                "SELECT owner_id, state, runner_id, consumed_at_ms FROM pairing_challenges "
                "WHERE challenge_id = ?",
                (created.payload["challengeId"],),
            ).fetchone()
        finally:
            inspection.close()
        self.assertEqual(state, (self.owner, "claimed", None, None))

        confirmed = self.control.confirm_pairing(
            self.owner,
            created.payload["challengeId"],
            approved=True,
            now=self.now,
        )
        self.assertEqual(confirmed.payload["state"], "active")

    def test_store_clock_prevents_nonce_retention_reset(self):
        paired = self.pair()
        original = self.signed(
            paired,
            path=RUNNER_PROBE_PATH,
            body=RUNNER_PROBE_BODY,
            nonce_bytes=b"n" * 16,
        )
        self.control.probe(original, now=self.now)

        jumped = self.now + dt.timedelta(seconds=901)
        ahead = self.signed(
            paired,
            path=RUNNER_PROBE_PATH,
            body=RUNNER_PROBE_BODY,
            now=jumped,
            nonce_bytes=b"j" * 16,
            advance_clock=False,
        )
        with self.assertRaises(SignedRequestError) as refused_jump:
            self.control.probe(ahead, now=jumped)
        self.assertEqual(refused_jump.exception.code, "runner_refused")

        with self.assertRaises(SignedRequestError) as replayed:
            self.control.probe(original, now=self.now)
        self.assertEqual(replayed.exception.code, "replayed_request")

    def test_concurrent_poll_is_one_attempt_with_recovery_under_repetition(self):
        paired = self.pair()
        for trial in range(20):
            current = self.now + dt.timedelta(seconds=trial)
            self.clock.current = current
            self.control.create_fixture_job(self.owner, paired["runner_id"], now=current)
            requests = [
                self.signed(
                    paired,
                    path=MATCH_JOB_POLL_PATH,
                    body=MATCH_JOB_POLL_BODY,
                    now=current,
                )
                for _ in range(2)
            ]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(
                    executor.map(lambda request: self.control.poll(request, now=current), requests)
                )
            attempts = {response.payload["attempt"]["attemptId"] for response in responses}
            recoveries = sorted(response.payload["recovery"] for response in responses)
            self.assertEqual(len(attempts), 1)
            self.assertEqual(recoveries, [False, True])
            grant = validate_poll_response(
                dict(responses[0].payload),
                profile=paired["profile"],
                request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
            )
            computation = compute_closed_fixture(grant)
            result_body = encode_result_request(grant, computation)
            self.control.result(
                self.signed(
                    paired,
                    path=MATCH_JOB_RESULT_PATH,
                    body=result_body,
                    now=current,
                ),
                now=current,
            )
        self.assertEqual(self.store.row_counts()["attempts"], 20)
        self.assertEqual(self.store.row_counts()["results"], 20)

    def test_expiry_redelivers_three_epochs_then_exhausts(self):
        paired = self.pair()
        self.control.create_fixture_job(self.owner, paired["runner_id"], now=self.now)
        epochs = []
        for offset in (0, 61, 122):
            current = self.now + dt.timedelta(seconds=offset)
            response = self.control.poll(
                self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY, now=current),
                now=current,
            )
            epochs.append(response.payload["attempt"]["leaseEpoch"])
        exhausted_at = self.now + dt.timedelta(seconds=183)
        exhausted = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY, now=exhausted_at),
            now=exhausted_at,
        )
        self.assertEqual(epochs, [1, 2, 3])
        self.assertEqual(exhausted.payload["status"], "exhausted")
        self.assertEqual(exhausted.payload["job"]["attemptsUsed"], 3)

    def test_abandon_requeues_and_renewal_cap_fails_closed(self):
        paired = self.pair()
        self.control.create_fixture_job(self.owner, paired["runner_id"], now=self.now)
        first = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY), now=self.now
        )
        attempt = first.payload["attempt"]
        renew_body = json.dumps({
            "jobId": first.payload["job"]["jobId"],
            "attemptId": attempt["attemptId"],
            "leaseEpoch": attempt["leaseEpoch"],
        }, separators=(",", ":")).encode()
        for expected in range(1, 6):
            response = self.control.renew(
                self.signed(paired, path=MATCH_JOB_RENEW_PATH, body=renew_body), now=self.now
            )
            self.assertEqual(response.payload["attempt"]["renewCount"], expected)
        inspection = sqlite3.connect(self.database)
        try:
            before_refusal = inspection.execute(
                "SELECT a.state, a.renew_count, a.lease_expires_at_ms, "
                "j.status, j.attempts_used FROM attempts a JOIN jobs j ON j.job_id = a.job_id "
                "WHERE a.attempt_id = ?",
                (attempt["attemptId"],),
            ).fetchone()
        finally:
            inspection.close()
        with self.assertRaises(HostedStoreError) as exhausted:
            self.control.renew(
                self.signed(paired, path=MATCH_JOB_RENEW_PATH, body=renew_body), now=self.now
            )
        self.assertEqual(exhausted.exception.code, "renewals_exhausted")
        inspection = sqlite3.connect(self.database)
        try:
            after_refusal = inspection.execute(
                "SELECT a.state, a.renew_count, a.lease_expires_at_ms, "
                "j.status, j.attempts_used FROM attempts a JOIN jobs j ON j.job_id = a.job_id "
                "WHERE a.attempt_id = ?",
                (attempt["attemptId"],),
            ).fetchone()
        finally:
            inspection.close()
        self.assertEqual(after_refusal, before_refusal)

        abandon_body = renew_body
        abandoned = self.control.abandon(
            self.signed(paired, path=MATCH_JOB_ABANDON_PATH, body=abandon_body), now=self.now
        )
        self.assertEqual(abandoned.payload["job"]["nextState"], "queued")
        second = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY), now=self.now
        )
        self.assertEqual(second.payload["attempt"]["leaseEpoch"], 2)

    def test_renewed_lease_accepts_result_after_the_original_deadline(self):
        paired = self.pair()
        self.control.create_fixture_job(self.owner, paired["runner_id"], now=self.now)
        polled = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY),
            now=self.now,
        )
        grant = validate_poll_response(
            dict(polled.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        renew_body = json.dumps({
            "jobId": grant.job.job_id,
            "attemptId": grant.attempt_id,
            "leaseEpoch": grant.lease_epoch,
        }, separators=(",", ":")).encode()
        renewed = self.control.renew(
            self.signed(paired, path=MATCH_JOB_RENEW_PATH, body=renew_body),
            now=self.now,
        )
        original_deadline = dt.datetime.fromisoformat(
            polled.payload["attempt"]["leaseExpiresAt"].replace("Z", "+00:00")
        )
        renewed_deadline = dt.datetime.fromisoformat(
            renewed.payload["attempt"]["leaseExpiresAt"].replace("Z", "+00:00")
        )
        after_original = original_deadline + dt.timedelta(milliseconds=1)
        self.assertLess(after_original, renewed_deadline)

        computation = compute_closed_fixture(grant)
        result_body = encode_result_request(grant, computation)
        recorded = self.control.result(
            self.signed(
                paired,
                path=MATCH_JOB_RESULT_PATH,
                body=result_body,
                now=after_original,
            ),
            now=after_original,
        )
        self.assertEqual(recorded.payload["status"], "recorded")
        self.assertFalse(recorded.payload["duplicate"])

    def test_bad_result_does_not_mutate_job_and_conflict_is_idempotent(self):
        paired = self.pair()
        self.control.create_fixture_job(self.owner, paired["runner_id"], now=self.now)
        polled = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY), now=self.now
        )
        grant = validate_poll_response(
            dict(polled.payload), profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        computation = compute_closed_fixture(grant)
        bad = json.loads(encode_result_request(grant, computation))
        bad["transcriptSha256"] = "0" * 64
        bad_body = json.dumps(bad, separators=(",", ":")).encode()
        inspection = sqlite3.connect(self.database)
        try:
            before_bad_result = inspection.execute(
                "SELECT a.state, a.completed_at_ms, j.status, j.updated_at_ms "
                "FROM attempts a JOIN jobs j ON j.job_id = a.job_id "
                "WHERE a.attempt_id = ?",
                (grant.attempt_id,),
            ).fetchone()
        finally:
            inspection.close()
        with self.assertRaises(HostedStoreError) as mismatch:
            self.control.result(
                self.signed(paired, path=MATCH_JOB_RESULT_PATH, body=bad_body), now=self.now
            )
        self.assertEqual(mismatch.exception.code, "transcript_mismatch")
        self.assertEqual(self.store.row_counts()["results"], 0)
        inspection = sqlite3.connect(self.database)
        try:
            after_bad_result = inspection.execute(
                "SELECT a.state, a.completed_at_ms, j.status, j.updated_at_ms "
                "FROM attempts a JOIN jobs j ON j.job_id = a.job_id "
                "WHERE a.attempt_id = ?",
                (grant.attempt_id,),
            ).fetchone()
        finally:
            inspection.close()
        self.assertEqual(after_bad_result, before_bad_result)

        good_body = encode_result_request(grant, computation)
        self.control.result(
            self.signed(paired, path=MATCH_JOB_RESULT_PATH, body=good_body), now=self.now
        )
        conflict = json.loads(good_body)
        conflict["outputSha256"] = "f" * 64
        conflict["transcriptSha256"] = fixture_transcript_sha256(
            job_id=grant.job.job_id,
            attempt_id=grant.attempt_id,
            lease_epoch=grant.lease_epoch,
            engine_sha256=MATCH_JOB_ENGINE_SHA256,
            input_sha256=grant.job.input_sha256,
            output_sha256=conflict["outputSha256"],
        )
        conflict_body = json.dumps(conflict, separators=(",", ":")).encode()
        with self.assertRaises(HostedStoreError) as conflict_error:
            self.control.result(
                self.signed(paired, path=MATCH_JOB_RESULT_PATH, body=conflict_body), now=self.now
            )
        self.assertEqual(conflict_error.exception.code, "result_conflict")
        self.assertEqual(self.store.row_counts()["results"], 1)

    def test_result_requires_the_jobs_current_runner_binding(self):
        paired = self.pair()
        replacement = self.pair(label="Replacement runner")
        self.control.create_fixture_job(self.owner, paired["runner_id"], now=self.now)
        polled = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY),
            now=self.now,
        )
        grant = validate_poll_response(
            dict(polled.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        self.assertIsInstance(grant, FixtureGrant)
        computation = compute_closed_fixture(grant)
        result_body = encode_result_request(grant, computation)

        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "UPDATE jobs SET runner_id = ? WHERE job_id = ?",
                (replacement["runner_id"], grant.job.job_id),
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(HostedStoreError) as stale_runner:
            self.control.result(
                self.signed(paired, path=MATCH_JOB_RESULT_PATH, body=result_body),
                now=self.now,
            )
        self.assertEqual(stale_runner.exception.code, "lease_inactive")
        self.assertEqual(self.store.row_counts()["results"], 0)
        self.assertEqual(self.store.row_counts()["replay_projections"], 0)

    def test_corrupt_or_poisoned_public_projection_uses_the_store_error_contract(self):
        paired = self.pair()
        grant = self.complete_job(paired, self.owner, now=self.now)
        connection = sqlite3.connect(self.database)
        try:
            for payload in (
                "{not-json",
                "[]",
                '{"schemaVersion":1,"ownerId":"must-not-escape"}',
            ):
                with self.subTest(payload=payload):
                    connection.execute(
                        "UPDATE replay_projections SET payload_json = ? WHERE job_id = ?",
                        (payload, grant.job.job_id),
                    )
                    connection.commit()
                    with self.assertRaises(HostedStoreError) as corrupt:
                        self.store.get_public_projection(grant.job.job_id)
                    self.assertEqual(corrupt.exception.code, "projection_corrupt")
        finally:
            connection.close()

    def test_mismatch_is_recorded_and_foreign_late_or_abandoned_results_are_refused(self):
        paired = self.pair()
        foreign = self.pair(owner=self.other_owner, label="Foreign runner")

        self.control.create_fixture_job(self.owner, paired["runner_id"], now=self.now)
        polled = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY),
            now=self.now,
        )
        grant = validate_poll_response(
            dict(polled.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        wrong_output = "f" * 64
        if compute_closed_fixture(grant).output_sha256 == wrong_output:
            wrong_output = "e" * 64
        mismatch_payload = {
            "jobId": grant.job.job_id,
            "attemptId": grant.attempt_id,
            "leaseEpoch": grant.lease_epoch,
            "engineSha256": MATCH_JOB_ENGINE_SHA256,
            "outputSha256": wrong_output,
            "transcriptSha256": fixture_transcript_sha256(
                job_id=grant.job.job_id,
                attempt_id=grant.attempt_id,
                lease_epoch=grant.lease_epoch,
                engine_sha256=MATCH_JOB_ENGINE_SHA256,
                input_sha256=grant.job.input_sha256,
                output_sha256=wrong_output,
            ),
        }
        mismatch_body = json.dumps(mismatch_payload, separators=(",", ":")).encode("ascii")
        recorded = self.control.result(
            self.signed(paired, path=MATCH_JOB_RESULT_PATH, body=mismatch_body),
            now=self.now,
        )
        self.assertEqual(recorded.payload["result"]["conformance"], "mismatch")
        self.assertEqual(
            self.control.public_replay(grant.job.job_id).payload["conformance"],
            "mismatch",
        )
        corrected = compute_closed_fixture(grant)
        corrected_body = encode_result_request(grant, corrected)
        with self.assertRaises(HostedStoreError) as corrected_after_mismatch:
            self.control.result(
                self.signed(paired, path=MATCH_JOB_RESULT_PATH, body=corrected_body),
                now=self.now,
            )
        self.assertEqual(corrected_after_mismatch.exception.code, "result_conflict")
        self.assertEqual(
            self.control.public_replay(grant.job.job_id).payload["conformance"],
            "mismatch",
        )
        with self.assertRaises(HostedStoreError) as foreign_duplicate:
            self.control.result(
                self.signed(foreign, path=MATCH_JOB_RESULT_PATH, body=mismatch_body),
                now=self.now,
            )
        self.assertEqual(foreign_duplicate.exception.code, "lease_inactive")

        next_time = self.now + dt.timedelta(seconds=1)
        self.clock.current = next_time
        self.control.create_fixture_job(self.owner, paired["runner_id"], now=next_time)
        second_poll = self.control.poll(
            self.signed(
                paired,
                path=MATCH_JOB_POLL_PATH,
                body=MATCH_JOB_POLL_BODY,
                now=next_time,
            ),
            now=next_time,
        )
        second_grant = validate_poll_response(
            dict(second_poll.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        second_computation = compute_closed_fixture(second_grant)
        second_body = encode_result_request(second_grant, second_computation)

        late = next_time + dt.timedelta(seconds=61)
        with self.assertRaises(HostedStoreError) as expired:
            self.control.result(
                self.signed(
                    paired,
                    path=MATCH_JOB_RESULT_PATH,
                    body=second_body,
                    now=late,
                ),
                now=late,
            )
        self.assertEqual(expired.exception.code, "lease_expired")

        redelivered = self.control.poll(
            self.signed(
                paired,
                path=MATCH_JOB_POLL_PATH,
                body=MATCH_JOB_POLL_BODY,
                now=late,
            ),
            now=late,
        )
        redelivered_grant = validate_poll_response(
            dict(redelivered.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        redelivered_computation = compute_closed_fixture(redelivered_grant)
        redelivered_body = encode_result_request(redelivered_grant, redelivered_computation)

        with self.assertRaises(HostedStoreError) as foreign_result:
            self.control.result(
                self.signed(
                    foreign,
                    path=MATCH_JOB_RESULT_PATH,
                    body=redelivered_body,
                    now=late,
                ),
                now=late,
            )
        self.assertEqual(foreign_result.exception.code, "lease_inactive")

        fake_attempt = "awa1_" + base64url_no_pad(b"z" * 16)
        wrong_attempt_payload = json.loads(redelivered_body)
        wrong_attempt_payload["attemptId"] = fake_attempt
        wrong_attempt_payload["transcriptSha256"] = fixture_transcript_sha256(
            job_id=redelivered_grant.job.job_id,
            attempt_id=fake_attempt,
            lease_epoch=redelivered_grant.lease_epoch,
            engine_sha256=MATCH_JOB_ENGINE_SHA256,
            input_sha256=redelivered_grant.job.input_sha256,
            output_sha256=redelivered_computation.output_sha256,
        )
        wrong_attempt_body = json.dumps(
            wrong_attempt_payload, separators=(",", ":")
        ).encode("ascii")
        with self.assertRaises(HostedStoreError) as wrong_attempt:
            self.control.result(
                self.signed(
                    paired,
                    path=MATCH_JOB_RESULT_PATH,
                    body=wrong_attempt_body,
                    now=late,
                ),
                now=late,
            )
        self.assertEqual(wrong_attempt.exception.code, "lease_inactive")

        abandon_body = json.dumps(
            {
                "jobId": redelivered_grant.job.job_id,
                "attemptId": redelivered_grant.attempt_id,
                "leaseEpoch": redelivered_grant.lease_epoch,
            },
            separators=(",", ":"),
        ).encode("ascii")
        self.control.abandon(
            self.signed(
                paired,
                path=MATCH_JOB_ABANDON_PATH,
                body=abandon_body,
                now=late,
            ),
            now=late,
        )
        with self.assertRaises(HostedStoreError) as abandoned:
            self.control.result(
                self.signed(
                    paired,
                    path=MATCH_JOB_RESULT_PATH,
                    body=redelivered_body,
                    now=late,
                ),
                now=late,
            )
        self.assertEqual(abandoned.exception.code, "lease_inactive")

    def test_runner_identity_path_method_and_protocol_binding(self):
        victim = self.pair()
        attacker = self.pair(owner=self.other_owner, label="Attacker")

        impersonated = self.signed(
            attacker,
            path=RUNNER_PROBE_PATH,
            body=RUNNER_PROBE_BODY,
            runner_id=victim["runner_id"],
            key=attacker["key"],
        )
        with self.assertRaises(SignedRequestError) as impersonation:
            self.control.probe(impersonated, now=self.now)
        self.assertEqual(impersonation.exception.code, "invalid_signature")

        wrong_path = self.signed(
            attacker,
            path=MATCH_JOB_RENEW_PATH,
            body=RUNNER_PROBE_BODY,
        )
        with self.assertRaises(SignedRequestError) as confused_path:
            self.control.probe(wrong_path, now=self.now)
        self.assertEqual(confused_path.exception.code, "wrong_path")

        put_renew = self.signed(
            attacker,
            path=MATCH_JOB_RENEW_PATH,
            body=b"{}",
            method="PUT",
        )
        with self.assertRaises(HostedStoreError) as wrong_method:
            self.control.renew(put_renew, now=self.now)
        self.assertEqual(wrong_method.exception.code, "invalid_renew")

        downgraded = self.signed(
            attacker,
            path=RUNNER_PROBE_PATH,
            body=RUNNER_PROBE_BODY,
            protocol_version="agentwars.runner_request.v1",
        )
        with self.assertRaises(SignedRequestError) as wrong_protocol:
            self.control.probe(downgraded, now=self.now)
        self.assertEqual(wrong_protocol.exception.code, "invalid_protocol")

    def test_server_origin_binding_rejects_host_confusion_without_nonce_burn(self):
        paired = self.pair()
        nonce_bytes = b"o" * 16
        before = self.store.row_counts()["nonces"]
        wrong_origin = self.signed(
            paired,
            origin="http://127.0.0.1:4173",
            path=RUNNER_PROBE_PATH,
            body=RUNNER_PROBE_BODY,
            nonce_bytes=nonce_bytes,
        )
        with self.assertRaises(SignedRequestError) as refused:
            self.control.probe(wrong_origin, now=self.now)
        self.assertEqual(refused.exception.code, "invalid_signature")
        self.assertEqual(self.store.row_counts()["nonces"], before)

        accepted = self.control.probe(
            self.signed(
                paired,
                origin=self.origin,
                path=RUNNER_PROBE_PATH,
                body=RUNNER_PROBE_BODY,
                nonce_bytes=nonce_bytes,
                advance_clock=False,
            ),
            now=self.now,
        )
        self.assertEqual(accepted.payload["status"], "accepted")
        self.assertEqual(self.store.row_counts()["nonces"], before + 1)

    def test_delete_owner_preserves_other_tenant_and_public_replay(self):
        first = self.pair(label="Private Alpha Label")
        second = self.pair(owner=self.other_owner, label="Private Beta Label")
        first_grant = self.complete_job(first, self.owner, now=self.now)
        second_time = self.now + dt.timedelta(seconds=1)
        second_grant = self.complete_job(second, self.other_owner, now=second_time)
        before = self.control.public_replay(second_grant.job.job_id)
        self.assertEqual(before.status_code, 200)

        self.control.delete_owner(self.owner)
        self.assertEqual(self.control.public_replay(first_grant.job.job_id).status_code, 404)
        after = self.control.public_replay(second_grant.job.job_id)
        self.assertEqual(after, before)
        self.assertEqual(
            self.store.get_runner(second["runner_id"], owner_id=self.other_owner).state,
            "active",
        )
        serialized = json.dumps(after.payload, sort_keys=True)
        for private_value in (
            self.other_owner,
            second["runner_id"],
            second["material"].fingerprint,
            "Private Beta Label",
            "4" * 64,
        ):
            self.assertNotIn(private_value, serialized)
        probe_time = second_time + dt.timedelta(seconds=1)
        accepted = self.control.probe(
            self.signed(
                second,
                path=RUNNER_PROBE_PATH,
                body=RUNNER_PROBE_BODY,
                now=probe_time,
            ),
            now=probe_time,
        )
        self.assertEqual(accepted.payload["status"], "accepted")

    def test_revocation_stale_future_and_wrong_signature_are_refused(self):
        paired = self.pair()
        stale = self.now - dt.timedelta(seconds=301)
        with self.assertRaises(SignedRequestError) as stale_error:
            self.control.probe(
                self.signed(paired, path=RUNNER_PROBE_PATH, body=RUNNER_PROBE_BODY, now=stale),
                now=self.now,
            )
        self.assertEqual(stale_error.exception.code, "stale_request")
        future = self.now + dt.timedelta(seconds=61)
        with self.assertRaises(SignedRequestError) as future_error:
            self.control.probe(
                self.signed(paired, path=RUNNER_PROBE_PATH, body=RUNNER_PROBE_BODY, now=future),
                now=self.now,
            )
        self.assertEqual(future_error.exception.code, "future_request")

        wrong = self.signed(paired, path=RUNNER_PROBE_PATH, body=RUNNER_PROBE_BODY)
        wrong = IncomingSignedRequest(**{**dataclass_dict(wrong), "signature": "A" * 86})
        with self.assertRaises(SignedRequestError) as signature_error:
            self.control.probe(wrong, now=self.now)
        self.assertEqual(signature_error.exception.code, "invalid_signature")

        self.control.create_fixture_job(self.owner, paired["runner_id"], now=self.now)
        self.control.create_fixture_job(self.owner, paired["runner_id"], now=self.now)
        leased = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY),
            now=self.now,
        )
        grant = validate_poll_response(
            dict(leased.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        self.assertIsInstance(grant, FixtureGrant)

        self.control.revoke_runner(self.owner, paired["runner_id"], now=self.now)
        # Duplicate revocation is idempotent and also repairs any unfinished
        # legacy rows that predate transactional terminalization.
        self.control.revoke_runner(self.owner, paired["runner_id"], now=self.now)
        inspection = sqlite3.connect(self.database)
        try:
            unfinished = inspection.execute(
                """SELECT COUNT(*) FROM jobs
                   WHERE runner_id = ? AND status IN ('queued', 'leased')""",
                (paired["runner_id"],),
            ).fetchone()[0]
            active_attempts = inspection.execute(
                "SELECT COUNT(*) FROM attempts WHERE runner_id = ? AND state = 'active'",
                (paired["runner_id"],),
            ).fetchone()[0]
            exhausted_jobs = inspection.execute(
                "SELECT COUNT(*) FROM jobs WHERE runner_id = ? AND status = 'exhausted'",
                (paired["runner_id"],),
            ).fetchone()[0]
            abandoned_attempts = inspection.execute(
                "SELECT COUNT(*) FROM attempts WHERE runner_id = ? AND state = 'abandoned'",
                (paired["runner_id"],),
            ).fetchone()[0]
        finally:
            inspection.close()
        self.assertEqual(unfinished, 0)
        self.assertEqual(active_attempts, 0)
        self.assertEqual(exhausted_jobs, 2)
        self.assertEqual(abandoned_attempts, 1)

        with self.assertRaises(SignedRequestError) as revoked:
            self.control.probe(
                self.signed(paired, path=RUNNER_PROBE_PATH, body=RUNNER_PROBE_BODY), now=self.now
            )
        self.assertEqual(revoked.exception.code, "runner_refused")

    def test_malformed_signed_json_is_rejected_before_nonce_consumption(self):
        paired = self.pair()
        duplicate_body = b'{"jobId":"x","jobId":"y","attemptId":"z","leaseEpoch":1}'
        request = self.manual_signed(
            paired, path=MATCH_JOB_RENEW_PATH, body=duplicate_body, now=self.now
        )
        with self.assertRaises(HostedStoreError) as duplicate:
            self.control.renew(request, now=self.now)
        self.assertEqual(duplicate.exception.code, "invalid_json")
        self.assertEqual(self.store.row_counts()["nonces"], 0)

        float_body = b'{"jobId":"x","attemptId":"z","leaseEpoch":1.0}'
        request = self.manual_signed(paired, path=MATCH_JOB_RENEW_PATH, body=float_body, now=self.now)
        with self.assertRaises(HostedStoreError) as floating:
            self.control.renew(request, now=self.now)
        self.assertEqual(floating.exception.code, "invalid_json")
        self.assertEqual(self.store.row_counts()["nonces"], 0)

        invalid_utf8 = b'\xff{"jobId":"x","attemptId":"z","leaseEpoch":1}'
        request = self.manual_signed(
            paired, path=MATCH_JOB_RENEW_PATH, body=invalid_utf8, now=self.now
        )
        with self.assertRaises(HostedStoreError) as malformed:
            self.control.renew(request, now=self.now)
        self.assertEqual(malformed.exception.code, "invalid_json")
        self.assertEqual(self.store.row_counts()["nonces"], 0)

    def test_strict_payload_fields_and_depth_reject_before_nonce_consumption(self):
        paired = self.pair()
        self.control.create_fixture_job(self.owner, paired["runner_id"], now=self.now)
        polled = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY),
            now=self.now,
        )
        grant = validate_poll_response(
            dict(polled.payload),
            profile=paired["profile"],
            request_body_sha256=hashlib.sha256(MATCH_JOB_POLL_BODY).hexdigest(),
        )
        nonce_count = self.store.row_counts()["nonces"]
        base = {
            "jobId": grant.job.job_id,
            "attemptId": grant.attempt_id,
            "leaseEpoch": grant.lease_epoch,
        }

        invalid_payloads = []
        invalid_payloads.append(({**base, "leaseEpoch": True}, "invalid_schema"))
        invalid_payloads.append(({**base, "leaseEpoch": MATCH_JOB_MAX_ATTEMPTS + 1}, "invalid_schema"))
        invalid_payloads.append(({**base, "unexpected": "field"}, "invalid_schema"))
        nested: object = "x"
        for _ in range(40):
            nested = [nested]
        invalid_payloads.append(({**base, "jobId": nested}, "invalid_json"))

        for payload, expected_code in invalid_payloads:
            body = json.dumps(payload, separators=(",", ":")).encode()
            request = self.manual_signed(
                paired,
                path=MATCH_JOB_RENEW_PATH,
                body=body,
                now=self.now,
            )
            with self.assertRaises(HostedStoreError) as refused:
                self.control.renew(request, now=self.now)
            self.assertEqual(refused.exception.code, expected_code)
            self.assertEqual(self.store.row_counts()["nonces"], nonce_count)

        computation = compute_closed_fixture(grant)
        result_payload = json.loads(encode_result_request(grant, computation))
        result_payload["engineSha256"] = result_payload["engineSha256"].upper()
        uppercase_body = json.dumps(result_payload, separators=(",", ":")).encode()
        with self.assertRaises(HostedStoreError) as uppercase:
            self.control.result(
                self.manual_signed(
                    paired,
                    path=MATCH_JOB_RESULT_PATH,
                    body=uppercase_body,
                    now=self.now,
                ),
                now=self.now,
            )
        self.assertEqual(uppercase.exception.code, "invalid_schema")
        self.assertEqual(self.store.row_counts()["nonces"], nonce_count)

    def test_envelope_body_binding_and_exact_timestamp_boundaries(self):
        paired = self.pair()
        nonce_count = self.store.row_counts()["nonces"]

        signed_probe = self.signed(
            paired,
            path=RUNNER_PROBE_PATH,
            body=RUNNER_PROBE_BODY,
            advance_clock=False,
        )
        mutable_body = IncomingSignedRequest(
            **{**dataclass_dict(signed_probe), "body": bytearray(RUNNER_PROBE_BODY)}
        )
        with self.assertRaises(SignedRequestError) as invalid_body_type:
            self.control.probe(mutable_body, now=self.now)
        self.assertEqual(invalid_body_type.exception.code, "invalid_request")
        self.assertEqual(self.store.row_counts()["nonces"], nonce_count)

        substituted = IncomingSignedRequest(
            **{**dataclass_dict(signed_probe), "body": b'{"probe":false}'}
        )
        with self.assertRaises(SignedRequestError) as body_substitution:
            verify_signed_request(
                self.store,
                substituted,
                expected_origin=self.origin,
                now=self.now,
                expected_path=RUNNER_PROBE_PATH,
            )
        self.assertEqual(body_substitution.exception.code, "invalid_signature")
        self.assertEqual(self.store.row_counts()["nonces"], nonce_count)

        for offset in (-MAX_REQUEST_AGE_SECONDS, MAX_REQUEST_FUTURE_SECONDS):
            boundary = self.now + dt.timedelta(seconds=offset)
            self.clock.current = self.now
            accepted = self.control.probe(
                self.signed(
                    paired,
                    path=RUNNER_PROBE_PATH,
                    body=RUNNER_PROBE_BODY,
                    now=boundary,
                    advance_clock=False,
                ),
                now=self.now,
            )
            self.assertEqual(accepted.payload["status"], "accepted")

        accepted_nonce_count = self.store.row_counts()["nonces"]
        for offset, code in (
            (-MAX_REQUEST_AGE_SECONDS - 0.001, "stale_request"),
            (MAX_REQUEST_FUTURE_SECONDS + 0.001, "future_request"),
        ):
            outside = self.now + dt.timedelta(seconds=offset)
            self.clock.current = self.now
            with self.assertRaises(SignedRequestError) as refused:
                self.control.probe(
                    self.signed(
                        paired,
                        path=RUNNER_PROBE_PATH,
                        body=RUNNER_PROBE_BODY,
                        now=outside,
                        advance_clock=False,
                    ),
                    now=self.now,
                )
            self.assertEqual(refused.exception.code, code)
            self.assertEqual(self.store.row_counts()["nonces"], accepted_nonce_count)

    def test_store_runner_validation_has_one_error_taxonomy(self):
        operations = (
            lambda: self.store.poll_job("not-a-runner", now=self.now),
            lambda: self.store.renew_attempt(
                "not-a-runner", "job", "attempt", 1, now=self.now
            ),
            lambda: self.store.abandon_attempt(
                "not-a-runner", "job", "attempt", 1, now=self.now
            ),
            lambda: self.store.record_result(
                "not-a-runner",
                job_id="job",
                attempt_id="attempt",
                lease_epoch=1,
                engine_sha256="0" * 64,
                output_sha256="0" * 64,
                transcript_sha256="0" * 64,
                now=self.now,
            ),
        )
        before_counts = self.store.row_counts()
        for operation in operations:
            with self.assertRaises(HostedStoreError) as invalid:
                operation()
            self.assertEqual(invalid.exception.code, "invalid_runner")
            self.assertEqual(self.store.row_counts(), before_counts)

    def test_owner_scope_is_enforced(self):
        paired = self.pair()
        with self.assertRaises(HostedStoreError) as wrong_owner:
            self.control.create_fixture_job(self.other_owner, paired["runner_id"], now=self.now)
        self.assertEqual(wrong_owner.exception.code, "runner_not_found")


def dataclass_dict(value):
    return {field.name: getattr(value, field.name) for field in value.__dataclass_fields__.values()}


if __name__ == "__main__":
    unittest.main()
