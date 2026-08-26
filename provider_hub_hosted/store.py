"""Durable state contract for the AgentWars hosted runner control plane.

SQLite is used here as a deterministic, locally testable reference for the
transactional semantics a production adapter must preserve.  This module does
not implement web authentication, provider authentication, provider calls, or
arbitrary code execution.
"""

from __future__ import annotations

import base64
import contextlib
import dataclasses
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import sqlite3
import threading
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from provider_hub.local_runner import (
    RUNNER_PROBE_EVIDENCE_CLASS,
    base64url_no_pad,
    claim_payload,
    parse_pairing_secret,
    validate_canonical_instant,
    validate_challenge_id,
    validate_fingerprint,
    validate_harness_id,
    validate_harness_version,
    validate_nonce,
    validate_runner_id,
)
from provider_hub.match_worker import (
    MATCH_JOB_ENGINE_ID,
    MATCH_JOB_ENGINE_SHA256,
    MATCH_JOB_KIND,
    MATCH_JOB_MAX_ATTEMPTS,
    MATCH_JOB_MAX_RENEWS,
    MATCH_JOB_RULESET_ID,
    MATCH_JOB_RULES_SHA256,
    derive_fixture_input,
    expected_fixture_output_sha256,
    fixture_transcript_sha256,
)


PAIRING_TTL_SECONDS = 600
PAIRING_MAX_CLAIM_ATTEMPTS = 8
LEASE_SECONDS = 60
NONCE_RETENTION_SECONDS = 900
MAX_REQUEST_AGE_SECONDS = 300
MAX_REQUEST_FUTURE_SECONDS = 60

_OWNER_ID_RE = re.compile(r"^awu1_[A-Za-z0-9_-]{22}$")
_JOB_ID_RE = re.compile(r"^awj1_[A-Za-z0-9_-]{22}$")
_ATTEMPT_ID_RE = re.compile(r"^awa1_[A-Za-z0-9_-]{22}$")
_SEED_RE = re.compile(r"^[A-Za-z0-9_-]{22}$")
_PUBLIC_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class HostedStoreError(ValueError):
    """A fail-closed hosted-state operation was refused."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclasses.dataclass(frozen=True)
class PairingChallenge:
    challenge_id: str
    pairing_secret: str = dataclasses.field(repr=False)
    expires_at: str = ""


@dataclasses.dataclass(frozen=True)
class PairingClaim:
    status: str
    challenge_id: str
    state: str
    fingerprint: str


@dataclasses.dataclass(frozen=True)
class PairingConfirmation:
    state: str
    challenge_id: str
    runner_id: str | None
    fingerprint: str | None


@dataclasses.dataclass(frozen=True)
class RunnerRecord:
    runner_id: str
    owner_id: str
    public_key: str
    fingerprint: str
    provider_id: str
    connection_mode: str
    display_label: str
    harness_id: str
    harness_version: str
    harness_digest: str
    state: str
    created_at: str
    revoked_at: str | None


@dataclasses.dataclass(frozen=True)
class FixtureJobRecord:
    job_id: str
    owner_id: str
    runner_id: str
    kind: str
    required_harness_id: str
    required_harness_digest: str
    engine_id: str
    engine_sha256: str
    ruleset_id: str
    rules_sha256: str
    seed: str
    input_sha256: str
    input_bytes_base64url: str
    max_attempts: int
    attempts_used: int
    status: str
    created_at: str


@dataclasses.dataclass(frozen=True)
class LeaseGrant:
    recovery: bool
    attempt_id: str
    lease_epoch: int
    attempt_number: int
    renew_count: int
    renewals_remaining: int
    lease_expires_at: str
    job: FixtureJobRecord


@dataclasses.dataclass(frozen=True)
class JobTerminal:
    status: str
    job_id: str
    attempts_used: int
    max_attempts: int
    result: Mapping[str, object] | None


@dataclasses.dataclass(frozen=True)
class ResultRecord:
    duplicate: bool
    result: Mapping[str, object]


def validate_owner_id(value: str) -> str:
    if not isinstance(value, str) or _OWNER_ID_RE.fullmatch(value) is None:
        raise HostedStoreError("invalid_owner", "owner id is invalid")
    return value


def _aware_utc(value: dt.datetime | None) -> dt.datetime:
    current = value or dt.datetime.now(dt.timezone.utc)
    if not isinstance(current, dt.datetime) or current.tzinfo is None:
        raise HostedStoreError("invalid_time", "time must be timezone-aware")
    return current.astimezone(dt.timezone.utc)


def _epoch_ms(value: dt.datetime | None) -> int:
    return int(_aware_utc(value).timestamp() * 1000)


def _instant_from_ms(value: int) -> str:
    instant = dt.datetime.fromtimestamp(value / 1000, tz=dt.timezone.utc)
    rendered = instant.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return validate_canonical_instant(rendered)


def _decode_base64url(value: str, expected_bytes: int, label: str) -> bytes:
    if not isinstance(value, str):
        raise HostedStoreError("invalid_encoding", f"{label} is invalid")
    try:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, TypeError) as error:
        raise HostedStoreError("invalid_encoding", f"{label} is invalid") from error
    if len(decoded) != expected_bytes or base64url_no_pad(decoded) != value:
        raise HostedStoreError("invalid_encoding", f"{label} is not canonical")
    return decoded


def _validate_token(value: str, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise HostedStoreError("invalid_identifier", f"{label} is invalid")
    token = value.split("_", 1)[1] if "_" in value else value
    _decode_base64url(token, 16, label)
    return value


def _digest(value: str, label: str) -> str:
    if not isinstance(value, str) or _HEX64_RE.fullmatch(value) is None:
        raise HostedStoreError("invalid_digest", f"{label} is invalid")
    return value


def _pairing_secret_digest(value: str) -> str:
    parse_pairing_secret(value)
    return hashlib.sha256(
        b"agentwars.pairing-secret-at-rest.v1\x00" + value.encode("ascii")
    ).hexdigest()


def _canonical_claim_digest(payload: Mapping[str, object], secret_digest: str) -> str:
    sanitized = {key: value for key, value in payload.items() if key != "pairingSecret"}
    sanitized["pairingSecretSha256"] = secret_digest
    encoded = json.dumps(
        sanitized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(b"agentwars.pairing-claim.v1\x00" + encoded).hexdigest()


def _public_key_and_fingerprint(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or _PUBLIC_KEY_RE.fullmatch(value) is None:
        raise HostedStoreError("invalid_public_key", "runner public key is invalid")
    raw = _decode_base64url(value, 32, "runner public key")
    try:
        Ed25519PublicKey.from_public_bytes(raw)
    except ValueError as error:
        raise HostedStoreError("invalid_public_key", "runner public key is invalid") from error
    return value, hashlib.sha256(raw).hexdigest()


class HostedControlPlaneStore:
    """Transactional reference store with one-writer atomic state changes."""

    def __init__(
        self,
        database: str | os.PathLike[str] = ":memory:",
        *,
        random_bytes: Callable[[int], bytes] = os.urandom,
        clock: Callable[[], dt.datetime] | None = None,
    ):
        if not callable(random_bytes):
            raise TypeError("random_bytes must be callable")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._random_bytes = random_bytes
        self._clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self._lock = threading.RLock()
        database_name = os.fspath(database)
        if database_name != ":memory:":
            database_name = os.fspath(Path(database_name).resolve())
        self._connection = sqlite3.connect(
            database_name,
            isolation_level=None,
            check_same_thread=False,
            timeout=10,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 10000")
        self._connection.execute("PRAGMA synchronous = FULL")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA trusted_schema = OFF")
        self._migrate()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "HostedControlPlaneStore":
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.close()

    @contextlib.contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
            except BaseException:
                self._connection.rollback()
                raise
            else:
                self._connection.commit()

    def _migrate(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS owners (
            owner_id TEXT PRIMARY KEY,
            created_at_ms INTEGER NOT NULL
        ) STRICT;

        CREATE TABLE IF NOT EXISTS pairing_challenges (
            challenge_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
            secret_sha256 TEXT UNIQUE,
            expires_at_ms INTEGER NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('prepared','claimed','confirmed','rejected','expired','locked')),
            claim_attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (claim_attempt_count BETWEEN 0 AND 8),
            claim_sha256 TEXT,
            public_key TEXT,
            fingerprint TEXT,
            provider_id TEXT,
            connection_mode TEXT,
            display_label TEXT,
            harness_id TEXT,
            harness_version TEXT,
            harness_digest TEXT,
            runner_id TEXT,
            created_at_ms INTEGER NOT NULL,
            claimed_at_ms INTEGER,
            consumed_at_ms INTEGER
        ) STRICT;

        CREATE TABLE IF NOT EXISTS runners (
            runner_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
            public_key TEXT NOT NULL UNIQUE,
            fingerprint TEXT NOT NULL UNIQUE,
            provider_id TEXT NOT NULL,
            connection_mode TEXT NOT NULL,
            display_label TEXT NOT NULL,
            harness_id TEXT NOT NULL,
            harness_version TEXT NOT NULL,
            harness_digest TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('active','revoked')),
            created_at_ms INTEGER NOT NULL,
            revoked_at_ms INTEGER
        ) STRICT;

        CREATE TABLE IF NOT EXISTS nonces (
            fingerprint TEXT NOT NULL,
            nonce TEXT NOT NULL,
            runner_id TEXT NOT NULL REFERENCES runners(runner_id) ON DELETE CASCADE,
            request_timestamp_ms INTEGER NOT NULL,
            body_sha256 TEXT NOT NULL,
            observed_at_ms INTEGER NOT NULL,
            PRIMARY KEY (fingerprint, nonce)
        ) WITHOUT ROWID, STRICT;

        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
            runner_id TEXT NOT NULL REFERENCES runners(runner_id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            required_harness_id TEXT NOT NULL,
            required_harness_digest TEXT NOT NULL,
            engine_id TEXT NOT NULL,
            engine_sha256 TEXT NOT NULL,
            ruleset_id TEXT NOT NULL,
            rules_sha256 TEXT NOT NULL,
            seed TEXT NOT NULL,
            input_sha256 TEXT NOT NULL,
            input_bytes_base64url TEXT NOT NULL,
            max_attempts INTEGER NOT NULL CHECK (max_attempts = 3),
            attempts_used INTEGER NOT NULL DEFAULT 0 CHECK (attempts_used BETWEEN 0 AND 3),
            status TEXT NOT NULL CHECK (status IN ('queued','leased','completed','exhausted')),
            created_at_ms INTEGER NOT NULL,
            updated_at_ms INTEGER NOT NULL
        ) STRICT;

        CREATE INDEX IF NOT EXISTS jobs_runner_status_created
            ON jobs(runner_id, status, created_at_ms, job_id);

        CREATE TABLE IF NOT EXISTS attempts (
            attempt_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
            runner_id TEXT NOT NULL REFERENCES runners(runner_id) ON DELETE CASCADE,
            lease_epoch INTEGER NOT NULL CHECK (lease_epoch BETWEEN 1 AND 3),
            state TEXT NOT NULL CHECK (state IN ('active','expired','abandoned','completed')),
            renew_count INTEGER NOT NULL DEFAULT 0 CHECK (renew_count BETWEEN 0 AND 5),
            lease_expires_at_ms INTEGER NOT NULL,
            created_at_ms INTEGER NOT NULL,
            completed_at_ms INTEGER,
            UNIQUE(job_id, lease_epoch)
        ) STRICT;

        CREATE UNIQUE INDEX IF NOT EXISTS one_active_attempt_per_job
            ON attempts(job_id) WHERE state = 'active';

        CREATE TABLE IF NOT EXISTS results (
            job_id TEXT PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
            attempt_id TEXT NOT NULL UNIQUE REFERENCES attempts(attempt_id) ON DELETE CASCADE,
            lease_epoch INTEGER NOT NULL,
            engine_sha256 TEXT NOT NULL,
            output_sha256 TEXT NOT NULL,
            transcript_sha256 TEXT NOT NULL,
            conformance TEXT NOT NULL CHECK (conformance IN ('match','mismatch')),
            completed_at_ms INTEGER NOT NULL
        ) STRICT;

        CREATE TABLE IF NOT EXISTS replay_projections (
            job_id TEXT PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
            payload_json TEXT NOT NULL,
            created_at_ms INTEGER NOT NULL
        ) STRICT;
        """
        with self._lock:
            try:
                self._connection.executescript("BEGIN IMMEDIATE;\n" + schema + "\nCOMMIT;")
            except BaseException:
                with contextlib.suppress(sqlite3.Error):
                    self._connection.rollback()
                raise

    def _new_token(self, prefix: str = "", *, size: int = 16) -> str:
        raw = self._random_bytes(size)
        if not isinstance(raw, bytes) or len(raw) != size:
            raise HostedStoreError("entropy_failure", "random source returned invalid bytes")
        return prefix + base64url_no_pad(raw)

    def create_pairing_challenge(
        self,
        owner_id: str,
        *,
        now: dt.datetime | None = None,
        ttl_seconds: int = PAIRING_TTL_SECONDS,
    ) -> PairingChallenge:
        owner_id = validate_owner_id(owner_id)
        if type(ttl_seconds) is not int or not 60 <= ttl_seconds <= PAIRING_TTL_SECONDS:
            raise HostedStoreError("invalid_ttl", "pairing ttl must be between 60 and 600 seconds")
        now_ms = _epoch_ms(now)
        expires_ms = now_ms + ttl_seconds * 1000
        for _ in range(8):
            challenge_id = self._new_token()
            random_code = self._new_token(size=24)
            secret = f"awp1_{challenge_id}_{random_code}"
            secret_sha256 = _pairing_secret_digest(secret)
            try:
                with self._transaction() as connection:
                    connection.execute(
                        "INSERT OR IGNORE INTO owners(owner_id, created_at_ms) VALUES (?, ?)",
                        (owner_id, now_ms),
                    )
                    connection.execute(
                        """INSERT INTO pairing_challenges(
                            challenge_id, owner_id, secret_sha256, expires_at_ms,
                            state, created_at_ms
                        ) VALUES (?, ?, ?, ?, 'prepared', ?)""",
                        (challenge_id, owner_id, secret_sha256, expires_ms, now_ms),
                    )
                return PairingChallenge(challenge_id, secret, _instant_from_ms(expires_ms))
            except sqlite3.IntegrityError:
                continue
        raise HostedStoreError("identifier_collision", "could not allocate a pairing challenge")

    def claim_pairing(
        self,
        payload: Mapping[str, object],
        *,
        now: dt.datetime | None = None,
    ) -> PairingClaim:
        if not isinstance(payload, Mapping):
            raise HostedStoreError("invalid_claim", "pairing claim is invalid")
        expected_keys = {
            "pairingSecret", "providerId", "connectionMode", "displayLabel",
            "harnessId", "harnessVersion", "harnessDigest", "publicKey",
        }
        if set(payload) != expected_keys:
            raise HostedStoreError("invalid_claim", "pairing claim has an invalid exact schema")
        try:
            validated = claim_payload(
                pairing_secret=payload["pairingSecret"],
                provider_id=payload["providerId"],
                display_label=payload["displayLabel"],
                harness_id=payload["harnessId"],
                harness_version=payload["harnessVersion"],
                harness_digest=payload["harnessDigest"],
                public_key=payload["publicKey"],
            )
        except (TypeError, ValueError) as error:
            raise HostedStoreError("invalid_claim", "pairing claim is invalid") from error
        if dict(payload) != validated:
            raise HostedStoreError("invalid_claim", "pairing claim is not canonical")
        challenge_id, _random_code = parse_pairing_secret(validated["pairingSecret"])
        secret_sha256 = _pairing_secret_digest(validated["pairingSecret"])
        public_key, fingerprint = _public_key_and_fingerprint(validated["publicKey"])
        claim_sha256 = _canonical_claim_digest(validated, secret_sha256)
        now_ms = _epoch_ms(now)

        deferred_error: HostedStoreError | None = None
        status: str | None = None
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM pairing_challenges WHERE challenge_id = ?",
                (challenge_id,),
            ).fetchone()
            if row is None:
                raise HostedStoreError("pairing_refused", "pairing claim was refused")
            if row["state"] in ("expired", "locked"):
                raise HostedStoreError("pairing_refused", "pairing claim was refused")
            if row["expires_at_ms"] <= now_ms and row["state"] not in ("confirmed", "rejected"):
                connection.execute(
                    "UPDATE pairing_challenges SET state = 'expired', secret_sha256 = NULL WHERE challenge_id = ?",
                    (challenge_id,),
                )
                deferred_error = HostedStoreError("pairing_expired", "pairing challenge expired")
            elif row["state"] == "prepared":
                if row["secret_sha256"] is None or not hmac.compare_digest(
                    row["secret_sha256"], secret_sha256
                ):
                    attempts = row["claim_attempt_count"] + 1
                    state = "locked" if attempts >= PAIRING_MAX_CLAIM_ATTEMPTS else "prepared"
                    connection.execute(
                        """UPDATE pairing_challenges
                           SET claim_attempt_count = ?, state = ?,
                               secret_sha256 = CASE WHEN ? = 'locked' THEN NULL ELSE secret_sha256 END
                           WHERE challenge_id = ?""",
                        (attempts, state, state, challenge_id),
                    )
                    deferred_error = HostedStoreError("pairing_refused", "pairing claim was refused")
                else:
                    connection.execute(
                        """UPDATE pairing_challenges SET
                            state = 'claimed', claim_attempt_count = claim_attempt_count + 1,
                            claim_sha256 = ?, public_key = ?, fingerprint = ?,
                            provider_id = ?, connection_mode = ?, display_label = ?,
                            harness_id = ?, harness_version = ?, harness_digest = ?,
                            claimed_at_ms = ?
                           WHERE challenge_id = ?""",
                        (
                            claim_sha256, public_key, fingerprint,
                            validated["providerId"], validated["connectionMode"],
                            validated["displayLabel"], validated["harnessId"],
                            validated["harnessVersion"], validated["harnessDigest"],
                            now_ms, challenge_id,
                        ),
                    )
                    status = "claimed"
            elif row["state"] == "claimed":
                if (
                    row["secret_sha256"] is None
                    or not hmac.compare_digest(row["secret_sha256"], secret_sha256)
                    or row["claim_sha256"] is None
                    or not hmac.compare_digest(row["claim_sha256"], claim_sha256)
                    or row["fingerprint"] is None
                    or not hmac.compare_digest(row["fingerprint"], fingerprint)
                ):
                    raise HostedStoreError("pairing_conflict", "pairing challenge already has a different claim")
                status = "duplicate"
            else:
                raise HostedStoreError("pairing_refused", "pairing claim was refused")
        if deferred_error is not None:
            raise deferred_error
        if status is None:
            raise HostedStoreError("pairing_refused", "pairing claim was refused")
        return PairingClaim(status, challenge_id, "pending_confirmation", fingerprint)

    def confirm_pairing(
        self,
        owner_id: str,
        challenge_id: str,
        *,
        approved: bool,
        now: dt.datetime | None = None,
    ) -> PairingConfirmation:
        owner_id = validate_owner_id(owner_id)
        try:
            challenge_id = validate_challenge_id(challenge_id)
        except ValueError as error:
            raise HostedStoreError("invalid_challenge", "challenge id is invalid") from error
        if type(approved) is not bool:
            raise HostedStoreError("invalid_decision", "pairing decision must be boolean")
        now_ms = _epoch_ms(now)
        deferred_error: HostedStoreError | None = None
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM pairing_challenges WHERE challenge_id = ? AND owner_id = ?",
                (challenge_id, owner_id),
            ).fetchone()
            if row is None:
                raise HostedStoreError("not_found", "pairing challenge was not found")
            if row["expires_at_ms"] <= now_ms and row["state"] not in ("confirmed", "rejected"):
                connection.execute(
                    "UPDATE pairing_challenges SET state = 'expired', secret_sha256 = NULL WHERE challenge_id = ?",
                    (challenge_id,),
                )
                deferred_error = HostedStoreError("pairing_expired", "pairing challenge expired")
            elif row["state"] == "confirmed":
                return PairingConfirmation("active", challenge_id, row["runner_id"], row["fingerprint"])
            elif row["state"] == "rejected":
                if approved:
                    raise HostedStoreError("pairing_rejected", "pairing challenge was already rejected")
                return PairingConfirmation("rejected", challenge_id, None, row["fingerprint"])
            elif row["state"] != "claimed":
                raise HostedStoreError("pairing_not_claimed", "pairing challenge is not ready for confirmation")
            elif not approved:
                connection.execute(
                    """UPDATE pairing_challenges
                       SET state = 'rejected', consumed_at_ms = ?, secret_sha256 = NULL
                       WHERE challenge_id = ?""",
                    (now_ms, challenge_id),
                )
                return PairingConfirmation("rejected", challenge_id, None, row["fingerprint"])
            else:
                runner_id = None
                for _ in range(8):
                    candidate = self._new_token("awr1_")
                    try:
                        connection.execute(
                            """INSERT INTO runners(
                                runner_id, owner_id, public_key, fingerprint,
                                provider_id, connection_mode, display_label,
                                harness_id, harness_version, harness_digest,
                                state, created_at_ms
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)""",
                            (
                                candidate, owner_id, row["public_key"], row["fingerprint"],
                                row["provider_id"], row["connection_mode"], row["display_label"],
                                row["harness_id"], row["harness_version"], row["harness_digest"],
                                now_ms,
                            ),
                        )
                        runner_id = candidate
                        break
                    except sqlite3.IntegrityError as error:
                        if "runner_id" not in str(error):
                            raise HostedStoreError(
                                "pairing_key_reused", "runner key is already paired"
                            ) from error
                if runner_id is None:
                    raise HostedStoreError("identifier_collision", "could not allocate a runner id")
                connection.execute(
                    """UPDATE pairing_challenges
                       SET state = 'confirmed', runner_id = ?, consumed_at_ms = ?, secret_sha256 = NULL
                       WHERE challenge_id = ?""",
                    (runner_id, now_ms, challenge_id),
                )
                return PairingConfirmation("active", challenge_id, runner_id, row["fingerprint"])
        if deferred_error is not None:
            raise deferred_error
        raise HostedStoreError("pairing_refused", "pairing confirmation was refused")

    def get_runner(self, runner_id: str, *, owner_id: str | None = None) -> RunnerRecord:
        try:
            runner_id = validate_runner_id(runner_id)
        except ValueError as error:
            raise HostedStoreError("invalid_runner", "runner id is invalid") from error
        if owner_id is not None:
            owner_id = validate_owner_id(owner_id)
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM runners WHERE runner_id = ?",
                (runner_id,),
            ).fetchone()
        if row is None or (owner_id is not None and row["owner_id"] != owner_id):
            raise HostedStoreError("runner_not_found", "runner was not found")
        return self._runner_from_row(row)

    def _runner_from_row(self, row: sqlite3.Row) -> RunnerRecord:
        return RunnerRecord(
            runner_id=row["runner_id"],
            owner_id=row["owner_id"],
            public_key=row["public_key"],
            fingerprint=row["fingerprint"],
            provider_id=row["provider_id"],
            connection_mode=row["connection_mode"],
            display_label=row["display_label"],
            harness_id=row["harness_id"],
            harness_version=row["harness_version"],
            harness_digest=row["harness_digest"],
            state=row["state"],
            created_at=_instant_from_ms(row["created_at_ms"]),
            revoked_at=(
                None if row["revoked_at_ms"] is None else _instant_from_ms(row["revoked_at_ms"])
            ),
        )

    def revoke_runner(
        self,
        owner_id: str,
        runner_id: str,
        *,
        now: dt.datetime | None = None,
    ) -> RunnerRecord:
        owner_id = validate_owner_id(owner_id)
        try:
            runner_id = validate_runner_id(runner_id)
        except ValueError as error:
            raise HostedStoreError("invalid_runner", "runner id is invalid") from error
        now_ms = _epoch_ms(now)
        expired = False
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM runners WHERE runner_id = ? AND owner_id = ?",
                (runner_id, owner_id),
            ).fetchone()
            if row is None:
                raise HostedStoreError("runner_not_found", "runner was not found")
            if row["state"] == "active":
                cursor = connection.execute(
                    "UPDATE runners SET state = 'revoked', revoked_at_ms = ? WHERE runner_id = ?",
                    (now_ms, runner_id),
                )
                if cursor.rowcount != 1:
                    raise HostedStoreError("runner_conflict", "runner revocation did not commit")
            # Runner-bound jobs cannot be reassigned after revocation. Preserve
            # their history, but terminalize every unfinished lease/job in the
            # same transaction so no active work can be stranded indefinitely.
            connection.execute(
                """UPDATE attempts
                   SET state = 'abandoned', completed_at_ms = ?
                   WHERE runner_id = ? AND state = 'active'""",
                (now_ms, runner_id),
            )
            connection.execute(
                """UPDATE jobs
                   SET status = 'exhausted', updated_at_ms = ?
                   WHERE runner_id = ? AND status IN ('queued', 'leased')""",
                (now_ms, runner_id),
            )
            row = connection.execute(
                "SELECT * FROM runners WHERE runner_id = ?", (runner_id,)
            ).fetchone()
        return self._runner_from_row(row)

    def delete_runner(self, owner_id: str, runner_id: str) -> int:
        owner_id = validate_owner_id(owner_id)
        try:
            runner_id = validate_runner_id(runner_id)
        except ValueError as error:
            raise HostedStoreError("invalid_runner", "runner id is invalid") from error
        with self._transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM runners WHERE runner_id = ? AND owner_id = ?",
                (runner_id, owner_id),
            )
            if cursor.rowcount != 1:
                raise HostedStoreError("runner_not_found", "runner was not found")
        return 1

    def delete_owner(self, owner_id: str) -> int:
        owner_id = validate_owner_id(owner_id)
        with self._transaction() as connection:
            cursor = connection.execute("DELETE FROM owners WHERE owner_id = ?", (owner_id,))
        return cursor.rowcount

    def consume_nonce(
        self,
        *,
        runner_id: str,
        fingerprint: str,
        nonce: str,
        request_timestamp_ms: int,
        body_sha256: str,
        expected_owner_id: str | None = None,
    ) -> None:
        try:
            runner_id = validate_runner_id(runner_id)
            fingerprint = validate_fingerprint(fingerprint)
        except ValueError as error:
            raise HostedStoreError("invalid_request_identity", "signed request identity is invalid") from error
        try:
            nonce = validate_nonce(nonce)
        except ValueError as error:
            raise HostedStoreError("invalid_nonce", "signed request nonce is invalid") from error
        body_sha256 = _digest(body_sha256, "request body digest")
        if expected_owner_id is not None:
            expected_owner_id = validate_owner_id(expected_owner_id)
        if type(request_timestamp_ms) is not int:
            raise HostedStoreError("invalid_time", "request time is invalid")
        observed_at_ms = _epoch_ms(self._clock())
        if (
            request_timestamp_ms < observed_at_ms - MAX_REQUEST_AGE_SECONDS * 1000
            or request_timestamp_ms > observed_at_ms + MAX_REQUEST_FUTURE_SECONDS * 1000
        ):
            raise HostedStoreError("invalid_time", "request time is outside the store acceptance window")
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT owner_id, fingerprint, state FROM runners WHERE runner_id = ?",
                (runner_id,),
            ).fetchone()
            if (
                row is None
                or row["state"] != "active"
                or not hmac.compare_digest(row["fingerprint"], fingerprint)
                or (expected_owner_id is not None and row["owner_id"] != expected_owner_id)
            ):
                raise HostedStoreError("runner_inactive", "runner request was refused")
            connection.execute(
                "DELETE FROM nonces WHERE observed_at_ms < ?",
                (observed_at_ms - NONCE_RETENTION_SECONDS * 1000,),
            )
            try:
                connection.execute(
                    """INSERT INTO nonces(
                        fingerprint, nonce, runner_id, request_timestamp_ms,
                        body_sha256, observed_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        fingerprint, nonce, runner_id, request_timestamp_ms,
                        body_sha256, observed_at_ms,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise HostedStoreError("replayed_request", "signed request nonce was already used") from error

    def create_fixture_job(
        self,
        owner_id: str,
        runner_id: str,
        *,
        seed: str | None = None,
        now: dt.datetime | None = None,
    ) -> FixtureJobRecord:
        owner_id = validate_owner_id(owner_id)
        runner = self.get_runner(runner_id, owner_id=owner_id)
        if runner.state != "active":
            raise HostedStoreError("runner_inactive", "runner is not active")
        if seed is None:
            seed = self._new_token()
        if not isinstance(seed, str) or _SEED_RE.fullmatch(seed) is None:
            raise HostedStoreError("invalid_seed", "fixture seed is invalid")
        _decode_base64url(seed, 16, "fixture seed")
        derived = derive_fixture_input(
            runner_id=runner.runner_id,
            harness_id=runner.harness_id,
            harness_digest=runner.harness_digest,
            seed=seed,
        )
        now_ms = _epoch_ms(now)
        for _ in range(8):
            job_id = self._new_token("awj1_")
            try:
                with self._transaction() as connection:
                    row = connection.execute(
                        "SELECT state FROM runners WHERE runner_id = ? AND owner_id = ?",
                        (runner_id, owner_id),
                    ).fetchone()
                    if row is None or row["state"] != "active":
                        raise HostedStoreError("runner_inactive", "runner is not active")
                    connection.execute(
                        """INSERT INTO jobs(
                            job_id, owner_id, runner_id, kind,
                            required_harness_id, required_harness_digest,
                            engine_id, engine_sha256, ruleset_id, rules_sha256,
                            seed, input_sha256, input_bytes_base64url,
                            max_attempts, attempts_used, status,
                            created_at_ms, updated_at_ms
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'queued', ?, ?)""",
                        (
                            job_id, owner_id, runner_id, MATCH_JOB_KIND,
                            runner.harness_id, runner.harness_digest,
                            MATCH_JOB_ENGINE_ID, MATCH_JOB_ENGINE_SHA256,
                            MATCH_JOB_RULESET_ID, MATCH_JOB_RULES_SHA256,
                            seed, derived["inputSha256"], derived["inputBytesBase64url"],
                            MATCH_JOB_MAX_ATTEMPTS, now_ms, now_ms,
                        ),
                    )
                    row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
                return self._job_from_row(row)
            except sqlite3.IntegrityError:
                continue
        raise HostedStoreError("identifier_collision", "could not allocate a match job")

    def _job_from_row(self, row: sqlite3.Row) -> FixtureJobRecord:
        return FixtureJobRecord(
            job_id=row["job_id"], owner_id=row["owner_id"], runner_id=row["runner_id"],
            kind=row["kind"], required_harness_id=row["required_harness_id"],
            required_harness_digest=row["required_harness_digest"],
            engine_id=row["engine_id"], engine_sha256=row["engine_sha256"],
            ruleset_id=row["ruleset_id"], rules_sha256=row["rules_sha256"],
            seed=row["seed"], input_sha256=row["input_sha256"],
            input_bytes_base64url=row["input_bytes_base64url"],
            max_attempts=row["max_attempts"], attempts_used=row["attempts_used"],
            status=row["status"], created_at=_instant_from_ms(row["created_at_ms"]),
        )

    def _expire_attempts(self, connection: sqlite3.Connection, runner_id: str, now_ms: int) -> None:
        rows = connection.execute(
            """SELECT a.attempt_id, a.job_id, j.attempts_used, j.max_attempts
               FROM attempts a JOIN jobs j ON j.job_id = a.job_id
               WHERE a.runner_id = ? AND a.state = 'active' AND a.lease_expires_at_ms <= ?""",
            (runner_id, now_ms),
        ).fetchall()
        for row in rows:
            connection.execute(
                "UPDATE attempts SET state = 'expired', completed_at_ms = ? WHERE attempt_id = ? AND state = 'active'",
                (now_ms, row["attempt_id"]),
            )
            status = "exhausted" if row["attempts_used"] >= row["max_attempts"] else "queued"
            connection.execute(
                "UPDATE jobs SET status = ?, updated_at_ms = ? WHERE job_id = ? AND status = 'leased'",
                (status, now_ms, row["job_id"]),
            )

    def poll_job(
        self,
        runner_id: str,
        *,
        now: dt.datetime | None = None,
        lease_seconds: int = LEASE_SECONDS,
    ) -> LeaseGrant | JobTerminal:
        try:
            runner_id = validate_runner_id(runner_id)
        except ValueError as error:
            raise HostedStoreError("invalid_runner", "runner id is invalid") from error
        if type(lease_seconds) is not int or not 5 <= lease_seconds <= 300:
            raise HostedStoreError("invalid_lease", "lease duration must be between 5 and 300 seconds")
        now_ms = _epoch_ms(now)
        with self._transaction() as connection:
            runner = connection.execute(
                "SELECT state FROM runners WHERE runner_id = ?", (runner_id,)
            ).fetchone()
            if runner is None or runner["state"] != "active":
                raise HostedStoreError("runner_inactive", "runner is not active")
            self._expire_attempts(connection, runner_id, now_ms)
            active = connection.execute(
                """SELECT a.*, j.*, j.created_at_ms AS job_created_at_ms
                   FROM attempts a JOIN jobs j ON j.job_id = a.job_id
                   WHERE a.runner_id = ? AND a.state = 'active'
                   ORDER BY a.created_at_ms, a.attempt_id LIMIT 1""",
                (runner_id,),
            ).fetchone()
            if active is not None:
                return self._grant_from_joined_row(active, recovery=True)
            job = connection.execute(
                """SELECT * FROM jobs WHERE runner_id = ? AND status = 'queued'
                   ORDER BY created_at_ms, job_id LIMIT 1""",
                (runner_id,),
            ).fetchone()
            if job is None:
                completed = connection.execute(
                    """SELECT j.*, r.attempt_id, r.lease_epoch, r.engine_sha256 AS result_engine_sha256,
                              r.output_sha256, r.transcript_sha256, r.conformance, r.completed_at_ms
                       FROM jobs j JOIN results r ON r.job_id = j.job_id
                       WHERE j.runner_id = ? AND j.status = 'completed'
                       ORDER BY r.completed_at_ms DESC, j.job_id LIMIT 1""",
                    (runner_id,),
                ).fetchone()
                if completed is not None:
                    return JobTerminal(
                        "completed", completed["job_id"], completed["attempts_used"],
                        completed["max_attempts"], self._public_result_from_joined_row(completed),
                    )
                exhausted = connection.execute(
                    """SELECT * FROM jobs WHERE runner_id = ? AND status = 'exhausted'
                       ORDER BY updated_at_ms DESC, job_id LIMIT 1""",
                    (runner_id,),
                ).fetchone()
                if exhausted is not None:
                    return JobTerminal(
                        "exhausted", exhausted["job_id"], exhausted["attempts_used"],
                        exhausted["max_attempts"], None,
                    )
                raise HostedStoreError("no_job", "no match job is available")
            next_epoch = job["attempts_used"] + 1
            if next_epoch > job["max_attempts"]:
                connection.execute(
                    "UPDATE jobs SET status = 'exhausted', updated_at_ms = ? WHERE job_id = ?",
                    (now_ms, job["job_id"]),
                )
                return JobTerminal("exhausted", job["job_id"], job["attempts_used"], job["max_attempts"], None)
            lease_expires_ms = now_ms + lease_seconds * 1000
            for _ in range(8):
                attempt_id = self._new_token("awa1_")
                try:
                    connection.execute(
                        """INSERT INTO attempts(
                            attempt_id, job_id, runner_id, lease_epoch, state,
                            renew_count, lease_expires_at_ms, created_at_ms
                        ) VALUES (?, ?, ?, ?, 'active', 0, ?, ?)""",
                        (attempt_id, job["job_id"], runner_id, next_epoch, lease_expires_ms, now_ms),
                    )
                    break
                except sqlite3.IntegrityError as error:
                    if "attempt_id" not in str(error):
                        raise
            else:
                raise HostedStoreError("identifier_collision", "could not allocate a match attempt")
            cursor = connection.execute(
                """UPDATE jobs SET attempts_used = ?, status = 'leased', updated_at_ms = ?
                   WHERE job_id = ? AND status = 'queued'""",
                (next_epoch, now_ms, job["job_id"]),
            )
            if cursor.rowcount != 1:
                raise HostedStoreError("lease_conflict", "match job was not claimed atomically")
            joined = connection.execute(
                """SELECT a.*, j.*, j.created_at_ms AS job_created_at_ms
                   FROM attempts a JOIN jobs j ON j.job_id = a.job_id
                   WHERE a.attempt_id = ?""",
                (attempt_id,),
            ).fetchone()
            return self._grant_from_joined_row(joined, recovery=False)

    def _grant_from_joined_row(self, row: sqlite3.Row, *, recovery: bool) -> LeaseGrant:
        job = dataclasses.replace(
            self._job_from_row(row),
            created_at=_instant_from_ms(row["job_created_at_ms"]),
        )
        return LeaseGrant(
            recovery=recovery,
            attempt_id=row["attempt_id"],
            lease_epoch=row["lease_epoch"],
            attempt_number=row["lease_epoch"],
            renew_count=row["renew_count"],
            renewals_remaining=MATCH_JOB_MAX_RENEWS - row["renew_count"],
            lease_expires_at=_instant_from_ms(row["lease_expires_at_ms"]),
            job=job,
        )

    def renew_attempt(
        self,
        runner_id: str,
        job_id: str,
        attempt_id: str,
        lease_epoch: int,
        *,
        now: dt.datetime | None = None,
        lease_seconds: int = LEASE_SECONDS,
    ) -> LeaseGrant:
        runner_id = validate_runner_id(runner_id)
        _validate_token(job_id, _JOB_ID_RE, "job id")
        _validate_token(attempt_id, _ATTEMPT_ID_RE, "attempt id")
        if type(lease_epoch) is not int or not 1 <= lease_epoch <= MATCH_JOB_MAX_ATTEMPTS:
            raise HostedStoreError("invalid_epoch", "lease epoch is invalid")
        if type(lease_seconds) is not int or not 5 <= lease_seconds <= 300:
            raise HostedStoreError("invalid_lease", "lease duration is invalid")
        now_ms = _epoch_ms(now)
        with self._transaction() as connection:
            runner = connection.execute("SELECT state FROM runners WHERE runner_id = ?", (runner_id,)).fetchone()
            if runner is None or runner["state"] != "active":
                raise HostedStoreError("runner_inactive", "runner is not active")
            row = connection.execute(
                """SELECT a.*, j.*, j.created_at_ms AS job_created_at_ms
                   FROM attempts a JOIN jobs j ON j.job_id = a.job_id
                   WHERE a.attempt_id = ? AND a.job_id = ? AND a.runner_id = ? AND a.lease_epoch = ?""",
                (attempt_id, job_id, runner_id, lease_epoch),
            ).fetchone()
            if row is None or row["state"] != "active" or row["status"] != "leased":
                raise HostedStoreError("lease_inactive", "match lease is not active")
            if row["lease_expires_at_ms"] <= now_ms:
                self._expire_attempts(connection, runner_id, now_ms)
                expired = True
            elif row["renew_count"] >= MATCH_JOB_MAX_RENEWS:
                raise HostedStoreError("renewals_exhausted", "match lease renewals are exhausted")
            else:
                renew_count = row["renew_count"] + 1
                expires_ms = max(now_ms, row["lease_expires_at_ms"]) + lease_seconds * 1000
                connection.execute(
                    "UPDATE attempts SET renew_count = ?, lease_expires_at_ms = ? WHERE attempt_id = ?",
                    (renew_count, expires_ms, attempt_id),
                )
                updated = connection.execute(
                    """SELECT a.*, j.*, j.created_at_ms AS job_created_at_ms
                       FROM attempts a JOIN jobs j ON j.job_id = a.job_id
                       WHERE a.attempt_id = ?""",
                    (attempt_id,),
                ).fetchone()
                return self._grant_from_joined_row(updated, recovery=True)
        if expired:
            raise HostedStoreError("lease_expired", "match lease expired")
        raise HostedStoreError("lease_inactive", "match lease is not active")

    def abandon_attempt(
        self,
        runner_id: str,
        job_id: str,
        attempt_id: str,
        lease_epoch: int,
        *,
        now: dt.datetime | None = None,
    ) -> JobTerminal:
        runner_id = validate_runner_id(runner_id)
        _validate_token(job_id, _JOB_ID_RE, "job id")
        _validate_token(attempt_id, _ATTEMPT_ID_RE, "attempt id")
        if type(lease_epoch) is not int or not 1 <= lease_epoch <= MATCH_JOB_MAX_ATTEMPTS:
            raise HostedStoreError("invalid_epoch", "lease epoch is invalid")
        now_ms = _epoch_ms(now)
        expired = False
        with self._transaction() as connection:
            runner = connection.execute(
                "SELECT state FROM runners WHERE runner_id = ?", (runner_id,)
            ).fetchone()
            if runner is None or runner["state"] != "active":
                raise HostedStoreError("runner_inactive", "runner is not active")
            row = connection.execute(
                """SELECT a.*, j.attempts_used, j.max_attempts, j.status AS job_status
                   FROM attempts a JOIN jobs j ON j.job_id = a.job_id
                   WHERE a.attempt_id = ? AND a.job_id = ? AND a.runner_id = ? AND a.lease_epoch = ?""",
                (attempt_id, job_id, runner_id, lease_epoch),
            ).fetchone()
            if row is None or row["state"] != "active" or row["job_status"] != "leased":
                raise HostedStoreError("lease_inactive", "match lease is not active")
            if row["lease_expires_at_ms"] <= now_ms:
                self._expire_attempts(connection, runner_id, now_ms)
                expired = True
            else:
                connection.execute(
                    "UPDATE attempts SET state = 'abandoned', completed_at_ms = ? WHERE attempt_id = ?",
                    (now_ms, attempt_id),
                )
                status = "exhausted" if row["attempts_used"] >= row["max_attempts"] else "queued"
                connection.execute(
                    "UPDATE jobs SET status = ?, updated_at_ms = ? WHERE job_id = ?",
                    (status, now_ms, job_id),
                )
                return JobTerminal(status, job_id, row["attempts_used"], row["max_attempts"], None)
        if expired:
            raise HostedStoreError("lease_expired", "match lease expired")
        raise HostedStoreError("lease_inactive", "match lease is not active")

    def record_result(
        self,
        runner_id: str,
        *,
        job_id: str,
        attempt_id: str,
        lease_epoch: int,
        engine_sha256: str,
        output_sha256: str,
        transcript_sha256: str,
        now: dt.datetime | None = None,
    ) -> ResultRecord:
        runner_id = validate_runner_id(runner_id)
        _validate_token(job_id, _JOB_ID_RE, "job id")
        _validate_token(attempt_id, _ATTEMPT_ID_RE, "attempt id")
        if type(lease_epoch) is not int or not 1 <= lease_epoch <= MATCH_JOB_MAX_ATTEMPTS:
            raise HostedStoreError("invalid_epoch", "lease epoch is invalid")
        engine_sha256 = _digest(engine_sha256, "engine digest")
        output_sha256 = _digest(output_sha256, "output digest")
        transcript_sha256 = _digest(transcript_sha256, "transcript digest")
        now_ms = _epoch_ms(now)
        expired = False
        with self._transaction() as connection:
            runner = connection.execute(
                "SELECT state FROM runners WHERE runner_id = ?", (runner_id,)
            ).fetchone()
            if runner is None or runner["state"] != "active":
                raise HostedStoreError("runner_inactive", "runner is not active")
            existing = connection.execute(
                """SELECT r.*, j.runner_id AS job_runner_id
                   FROM results r JOIN jobs j ON j.job_id = r.job_id
                   WHERE r.job_id = ?""",
                (job_id,),
            ).fetchone()
            if existing is not None:
                if not hmac.compare_digest(existing["job_runner_id"], runner_id):
                    raise HostedStoreError("lease_inactive", "match lease is not active")
                supplied = (
                    attempt_id, lease_epoch, engine_sha256, output_sha256, transcript_sha256
                )
                recorded = (
                    existing["attempt_id"], existing["lease_epoch"], existing["engine_sha256"],
                    existing["output_sha256"], existing["transcript_sha256"],
                )
                if supplied != recorded:
                    raise HostedStoreError("result_conflict", "job already has a different result")
                return ResultRecord(True, self._public_result_from_result_row(existing))

            row = connection.execute(
                """SELECT a.*, j.* FROM attempts a JOIN jobs j ON j.job_id = a.job_id
                   WHERE a.attempt_id = ? AND a.job_id = ? AND a.runner_id = ? AND a.lease_epoch = ?""",
                (attempt_id, job_id, runner_id, lease_epoch),
            ).fetchone()
            if row is None or row["state"] != "active" or row["status"] != "leased":
                raise HostedStoreError("lease_inactive", "match lease is not active")
            if row["lease_expires_at_ms"] <= now_ms:
                self._expire_attempts(connection, runner_id, now_ms)
                expired = True
            elif not hmac.compare_digest(engine_sha256, row["engine_sha256"]):
                raise HostedStoreError("engine_mismatch", "result changed the fixture engine")
            else:
                expected_transcript = fixture_transcript_sha256(
                    job_id=job_id,
                    attempt_id=attempt_id,
                    lease_epoch=lease_epoch,
                    engine_sha256=engine_sha256,
                    input_sha256=row["input_sha256"],
                    output_sha256=output_sha256,
                )
                if not hmac.compare_digest(transcript_sha256, expected_transcript):
                    raise HostedStoreError("transcript_mismatch", "result transcript commitment is invalid")
                expected_output = expected_fixture_output_sha256(row["input_bytes_base64url"])
                conformance = "match" if hmac.compare_digest(output_sha256, expected_output) else "mismatch"
                connection.execute(
                    """INSERT INTO results(
                        job_id, attempt_id, lease_epoch, engine_sha256, output_sha256,
                        transcript_sha256, conformance, completed_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        job_id, attempt_id, lease_epoch, engine_sha256, output_sha256,
                        transcript_sha256, conformance, now_ms,
                    ),
                )
                cursor = connection.execute(
                    """UPDATE attempts SET state = 'completed', completed_at_ms = ?
                       WHERE attempt_id = ? AND state = 'active'""",
                    (now_ms, attempt_id),
                )
                if cursor.rowcount != 1:
                    raise HostedStoreError("lease_conflict", "match attempt was not completed atomically")
                cursor = connection.execute(
                    """UPDATE jobs SET status = 'completed', updated_at_ms = ?
                       WHERE job_id = ? AND status = 'leased'""",
                    (now_ms, job_id),
                )
                if cursor.rowcount != 1:
                    raise HostedStoreError("lease_conflict", "match job was not completed atomically")
                result = {
                    "jobId": job_id,
                    "attemptId": attempt_id,
                    "leaseEpoch": lease_epoch,
                    "engineSha256": engine_sha256,
                    "outputSha256": output_sha256,
                    "transcriptSha256": transcript_sha256,
                    "conformance": conformance,
                    "completedAt": _instant_from_ms(now_ms),
                }
                projection = self._build_projection(row, result)
                connection.execute(
                    "INSERT INTO replay_projections(job_id, payload_json, created_at_ms) VALUES (?, ?, ?)",
                    (
                        job_id,
                        json.dumps(projection, sort_keys=True, separators=(",", ":"), allow_nan=False),
                        now_ms,
                    ),
                )
                return ResultRecord(False, result)
        if expired:
            raise HostedStoreError("lease_expired", "match lease expired")
        raise HostedStoreError("lease_inactive", "match lease is not active")

    def _public_result_from_result_row(self, row: sqlite3.Row) -> Mapping[str, object]:
        return {
            "jobId": row["job_id"],
            "attemptId": row["attempt_id"],
            "leaseEpoch": row["lease_epoch"],
            "engineSha256": row["engine_sha256"],
            "outputSha256": row["output_sha256"],
            "transcriptSha256": row["transcript_sha256"],
            "conformance": row["conformance"],
            "completedAt": _instant_from_ms(row["completed_at_ms"]),
        }

    def _public_result_from_joined_row(self, row: sqlite3.Row) -> Mapping[str, object]:
        return {
            "jobId": row["job_id"],
            "attemptId": row["attempt_id"],
            "leaseEpoch": row["lease_epoch"],
            "engineSha256": row["result_engine_sha256"],
            "outputSha256": row["output_sha256"],
            "transcriptSha256": row["transcript_sha256"],
            "conformance": row["conformance"],
            "completedAt": _instant_from_ms(row["completed_at_ms"]),
        }

    def _build_projection(
        self,
        job_row: sqlite3.Row,
        result: Mapping[str, object],
    ) -> Mapping[str, object]:
        return {
            "schemaVersion": 1,
            "projectionType": "agentwars.fixture_replay.v1",
            "jobId": result["jobId"],
            "attemptId": result["attemptId"],
            "leaseEpoch": result["leaseEpoch"],
            "kind": MATCH_JOB_KIND,
            "engineId": job_row["engine_id"],
            "engineSha256": result["engineSha256"],
            "rulesetId": job_row["ruleset_id"],
            "rulesSha256": job_row["rules_sha256"],
            "outputSha256": result["outputSha256"],
            "transcriptSha256": result["transcriptSha256"],
            "conformance": result["conformance"],
            "completedAt": result["completedAt"],
            "evidenceClass": RUNNER_PROBE_EVIDENCE_CLASS,
            "providerAccountAttested": False,
            "planEntitlementAttested": False,
            "billingRouteAttested": False,
            "modelAttested": False,
            "personAttested": False,
            "runtimeAttested": False,
            "harnessExecutionAttested": False,
            "matchExecutionAttested": False,
        }

    def get_public_projection(self, job_id: str) -> Mapping[str, object] | None:
        _validate_token(job_id, _JOB_ID_RE, "job id")
        with self._lock:
            row = self._connection.execute(
                "SELECT payload_json FROM replay_projections WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        value = json.loads(row["payload_json"])
        if not isinstance(value, dict):
            raise HostedStoreError("projection_corrupt", "public projection is invalid")
        return value

    def row_counts(self) -> Mapping[str, int]:
        tables = (
            "owners", "pairing_challenges", "runners", "nonces", "jobs",
            "attempts", "results", "replay_projections",
        )
        with self._lock:
            return {
                table: self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in tables
            }
