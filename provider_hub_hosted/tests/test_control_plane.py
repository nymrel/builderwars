from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provider_hub.local_runner import (
    PAIRING_PROTOCOL,
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
from provider_hub_hosted.store import HostedControlPlaneStore, HostedStoreError
from provider_hub_hosted.verify import (
    IncomingSignedRequest,
    SignedRequestError,
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


def owner_id(byte: int) -> str:
    return "awu1_" + base64url_no_pad(bytes([byte]) * 16)


class HostedControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="agentwars-hosted-test-")
        self.database = Path(self.temporary.name) / "control-plane.sqlite3"
        self.random = DeterministicBytes()
        self.store = HostedControlPlaneStore(self.database, random_bytes=self.random)
        self.control = HostedControlPlane(self.store)
        self.owner = owner_id(1)
        self.other_owner = owner_id(2)
        self.now = START
        self.nonce_counter = 0

    def tearDown(self):
        self.store.close()
        self.temporary.cleanup()

    def pair(self, *, owner=None, label="Sunday Machine", now=None):
        owner = owner or self.owner
        now = now or self.now
        created = self.control.create_pairing(owner, now=now)
        secret = created.payload["pairingSecret"]
        challenge_id = created.payload["challengeId"]
        key = Ed25519PrivateKey.generate()
        material = public_key_material(key)
        payload = claim_payload(
            pairing_secret=secret,
            provider_id="chatgpt_codex",
            display_label=label,
            harness_id="agentwars-fixture",
            harness_version="1.0.0",
            harness_digest="4" * 64,
            public_key=material.public_key,
        )
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
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

    def signed(self, paired, *, path, body, now=None):
        now = now or self.now
        self.nonce_counter += 1
        nonce = self.nonce_counter.to_bytes(16, "big")
        signed = sign_runner_request(
            paired["key"],
            method="POST",
            path=path,
            body=body,
            runner_id=paired["runner_id"],
            timestamp=canonical_instant(now),
            nonce_bytes=nonce,
        )
        return IncomingSignedRequest(
            method=signed.method,
            path=signed.path,
            body=signed.body,
            protocol_version=REQUEST_PROTOCOL,
            runner_id=signed.runner_id,
            timestamp=signed.timestamp,
            nonce=signed.nonce,
            signature=signed.signature,
        )

    def manual_signed(self, paired, *, path, body, now=None):
        now = now or self.now
        self.nonce_counter += 1
        nonce = base64url_no_pad(self.nonce_counter.to_bytes(16, "big"))
        stamp = canonical_instant(now)
        body_sha256 = hashlib.sha256(body).hexdigest()
        canonical = canonical_runner_request(
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
        self.store = HostedControlPlaneStore(self.database, random_bytes=self.random)
        self.control = HostedControlPlane(self.store)

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

    def test_concurrent_poll_is_one_attempt_with_recovery(self):
        paired = self.pair()
        self.control.create_fixture_job(self.owner, paired["runner_id"], now=self.now)
        requests = [
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY)
            for _ in range(2)
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda request: self.control.poll(request, now=self.now), requests))
        attempts = {response.payload["attempt"]["attemptId"] for response in responses}
        recoveries = sorted(response.payload["recovery"] for response in responses)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(recoveries, [False, True])
        self.assertEqual(self.store.row_counts()["attempts"], 1)

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
        with self.assertRaises(HostedStoreError) as exhausted:
            self.control.renew(
                self.signed(paired, path=MATCH_JOB_RENEW_PATH, body=renew_body), now=self.now
            )
        self.assertEqual(exhausted.exception.code, "renewals_exhausted")

        abandon_body = renew_body
        abandoned = self.control.abandon(
            self.signed(paired, path=MATCH_JOB_ABANDON_PATH, body=abandon_body), now=self.now
        )
        self.assertEqual(abandoned.payload["job"]["nextState"], "queued")
        second = self.control.poll(
            self.signed(paired, path=MATCH_JOB_POLL_PATH, body=MATCH_JOB_POLL_BODY), now=self.now
        )
        self.assertEqual(second.payload["attempt"]["leaseEpoch"], 2)

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
        with self.assertRaises(HostedStoreError) as mismatch:
            self.control.result(
                self.signed(paired, path=MATCH_JOB_RESULT_PATH, body=bad_body), now=self.now
            )
        self.assertEqual(mismatch.exception.code, "transcript_mismatch")
        self.assertEqual(self.store.row_counts()["results"], 0)

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

        self.control.revoke_runner(self.owner, paired["runner_id"], now=self.now)
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

    def test_owner_scope_is_enforced(self):
        paired = self.pair()
        with self.assertRaises(HostedStoreError) as wrong_owner:
            self.control.create_fixture_job(self.other_owner, paired["runner_id"], now=self.now)
        self.assertEqual(wrong_owner.exception.code, "runner_not_found")


def dataclass_dict(value):
    return {field.name: getattr(value, field.name) for field in value.__dataclass_fields__.values()}


if __name__ == "__main__":
    unittest.main()
