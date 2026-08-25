"""Encrypted local key custody and public runner-profile state.

Private keys are passphrase-encrypted PKCS#8 files written by the maintained
``agent_identity.keys`` primitives.  Pairing secrets and passphrases never
enter this store.  The adjacent JSON profile is deliberately public metadata
and keeps every provider/model/runtime/execution attestation false.

The store serializes local mutations with an OS file lock and uses same-folder
atomic replacement for profile updates.  Windows ACL strength is not inferred;
confidentiality there rests on the encrypted PKCS#8 passphrase.  POSIX state
directories and files additionally fail closed on group/other permissions.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import stat
import sys
from pathlib import Path

from agent_identity.keys import (
    KeyMaterialError,
    generate_private_key,
    load_private_key_file,
    save_private_key_encrypted,
)
from provider_hub.catalog import PROVIDER_IDS, connection_mode_for
from provider_hub.local_runner import (
    PAIRING_PROTOCOL,
    RunnerClientError,
    canonical_instant,
    public_key_material,
    validate_challenge_id,
    validate_display_label,
    validate_fingerprint,
    validate_harness_id,
    validate_harness_version,
    validate_origin,
    validate_runner_id,
)


PROFILE_SCHEMA = "agentwars.local_runner_profile.v1"
PROFILE_STATES = (
    "prepared",
    "pending_confirmation",
    "runner_id_recorded_unverified",
)
CLAIM_STATUSES = ("not_confirmed", "claimed", "duplicate")
MAX_PROFILE_BYTES = 32 * 1024
_KEY_FILE_RE = re.compile(r"^key-([A-Za-z0-9_-]{22})\.pem$")
_PROFILE_FILE_RE = re.compile(r"^profile-([A-Za-z0-9_-]{22})\.json$")
_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
_INSTANT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

_PROFILE_KEYS = frozenset(
    {
        "schema",
        "protocolVersion",
        "challengeId",
        "runnerId",
        "localState",
        "serverClaimStatus",
        "endpointOrigin",
        "providerId",
        "connectionMode",
        "displayLabel",
        "harnessId",
        "harnessVersion",
        "harnessDigest",
        "publicKey",
        "fingerprint",
        "keyFile",
        "createdAt",
        "updatedAt",
        "localEvidenceClass",
        "accountApprovalAttested",
        "providerAccountAttested",
        "planEntitlementAttested",
        "billingRouteAttested",
        "modelAttested",
        "personAttested",
        "runtimeAttested",
        "harnessExecutionAttested",
        "matchExecutionAttested",
    }
)


class RunnerStateError(RunnerClientError):
    """Local encrypted state could not be read or changed safely."""


def default_state_directory() -> Path:
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA")
        if not root:
            raise RunnerStateError("LOCALAPPDATA is unavailable; pass --state-dir explicitly")
        return Path(root) / "Nymrel" / "AgentWars" / "runners"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Nymrel" / "AgentWars" / "runners"
    root = os.environ.get("XDG_DATA_HOME")
    base = Path(root) if root else Path.home() / ".local" / "share"
    return base / "nymrel" / "agentwars" / "runners"


class RunnerStateStore:
    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = Path(root) if root is not None else default_state_directory()

    def ensure(self) -> Path:
        absolute = self.root.expanduser().resolve(strict=False)
        if self.root.exists() and self.root.is_symlink():
            raise RunnerStateError("runner state directory must not be a symlink")
        try:
            absolute.mkdir(parents=True, mode=0o700, exist_ok=True)
        except OSError as error:
            raise RunnerStateError("runner state directory could not be created") from error
        try:
            info = absolute.lstat()
        except OSError as error:
            raise RunnerStateError("runner state directory could not be inspected") from error
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise RunnerStateError("runner state path must be a real directory")
        if os.name != "nt":
            if hasattr(os, "getuid") and info.st_uid != os.getuid():
                raise RunnerStateError("runner state directory must be owned by the current user")
            try:
                os.chmod(absolute, 0o700)
                info = absolute.lstat()
            except OSError as error:
                raise RunnerStateError("runner state directory permissions could not be restricted") from error
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise RunnerStateError("runner state directory is accessible to another POSIX user")
        self.root = absolute
        return absolute

    def profile_path(self, challenge_id: str) -> Path:
        return self.ensure() / f"profile-{validate_challenge_id(challenge_id)}.json"

    def key_path(self, challenge_id: str) -> Path:
        return self.ensure() / f"key-{validate_challenge_id(challenge_id)}.pem"

    @contextlib.contextmanager
    def locked(self):
        root = self.ensure()
        lock_path = root / ".state.lock"
        if lock_path.is_symlink():
            raise RunnerStateError("runner state lock must not be a symlink")
        flags = (
            os.O_RDWR
            | os.O_CREAT
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as error:
            raise RunnerStateError("runner state lock could not be opened") from error
        try:
            opened = os.fstat(descriptor)
            linked = os.lstat(lock_path)
            if (
                not stat.S_ISREG(opened.st_mode)
                or stat.S_ISLNK(linked.st_mode)
                or opened.st_dev != linked.st_dev
                or opened.st_ino != linked.st_ino
                or getattr(opened, "st_nlink", 1) != 1
                or opened.st_size not in (0, 1)
            ):
                raise RunnerStateError("runner state lock path is unsafe")
            if os.name != "nt":
                if hasattr(os, "getuid") and opened.st_uid != os.getuid():
                    raise RunnerStateError("runner state lock must be owned by the current user")
                if stat.S_IMODE(opened.st_mode) & 0o077:
                    raise RunnerStateError("runner state lock is accessible to another POSIX user")
            if os.name == "nt":
                import msvcrt

                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b"0")
                    os.fsync(descriptor)
                os.lseek(descriptor, 0, os.SEEK_SET)
                try:
                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                except OSError as error:
                    raise RunnerStateError("another AgentWars runner process is changing local state") from error
            else:
                import fcntl

                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as error:
                    raise RunnerStateError("another AgentWars runner process is changing local state") from error
            yield
        finally:
            try:
                if os.name == "nt":
                    import msvcrt

                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(descriptor)

    def prepare(
        self,
        *,
        challenge_id: str,
        passphrase: bytes,
        endpoint_origin: str,
        provider_id: str,
        display_label: str,
        harness_id: str,
        harness_version: str,
        harness_digest: str,
    ):
        """Create or recover one encrypted key and exact public profile.

        If an ambiguous earlier run left a key or complete profile, retry reuses
        that exact key.  It never rotates the candidate behind an already-used
        pairing secret.
        """
        challenge_id = validate_challenge_id(challenge_id)
        candidate = _validated_candidate(
            endpoint_origin=endpoint_origin,
            provider_id=provider_id,
            display_label=display_label,
            harness_id=harness_id,
            harness_version=harness_version,
            harness_digest=harness_digest,
        )
        with self.locked():
            profile_path = self.profile_path(challenge_id)
            key_path = self.key_path(challenge_id)
            if profile_path.exists():
                profile = self._read_profile_path(profile_path)
                _require_same_candidate(profile, candidate)
                key = self._load_key_path(key_path, passphrase)
                _require_key_matches_profile(key, profile)
                return profile, key, False

            key_created = False
            if key_path.exists():
                if key_path.is_symlink():
                    raise RunnerStateError("runner private-key path must not be a symlink")
                key = self._load_key_path(key_path, passphrase)
            else:
                key = generate_private_key()
                try:
                    save_private_key_encrypted(key_path, key, passphrase, overwrite=False)
                except KeyMaterialError as error:
                    raise RunnerStateError(str(error)) from error
                key_created = True
            material = public_key_material(key)
            stamp = canonical_instant()
            profile = {
                "schema": PROFILE_SCHEMA,
                "protocolVersion": PAIRING_PROTOCOL,
                "challengeId": challenge_id,
                "runnerId": None,
                "localState": "prepared",
                "serverClaimStatus": "not_confirmed",
                "endpointOrigin": candidate["endpointOrigin"],
                "providerId": candidate["providerId"],
                "connectionMode": candidate["connectionMode"],
                "displayLabel": candidate["displayLabel"],
                "harnessId": candidate["harnessId"],
                "harnessVersion": candidate["harnessVersion"],
                "harnessDigest": candidate["harnessDigest"],
                "publicKey": material.public_key,
                "fingerprint": material.fingerprint,
                "keyFile": key_path.name,
                "createdAt": stamp,
                "updatedAt": stamp,
                "localEvidenceClass": "local_ed25519_key_only",
                "accountApprovalAttested": False,
                "providerAccountAttested": False,
                "planEntitlementAttested": False,
                "billingRouteAttested": False,
                "modelAttested": False,
                "personAttested": False,
                "runtimeAttested": False,
                "harnessExecutionAttested": False,
                "matchExecutionAttested": False,
            }
            profile = validate_profile(profile)
            try:
                self._write_profile_path(profile_path, profile, replace=False)
            except Exception:
                if key_created:
                    try:
                        key_path.unlink()
                    except OSError:
                        pass
                raise
            return profile, key, True

    def mark_claim_accepted(self, challenge_id: str, status: str) -> dict[str, object]:
        if status not in ("claimed", "duplicate"):
            raise RunnerStateError("server claim status is invalid")
        with self.locked():
            path = self.profile_path(challenge_id)
            profile = self._read_profile_path(path)
            if profile["localState"] == "runner_id_recorded_unverified":
                if profile["serverClaimStatus"] != status:
                    raise RunnerStateError("runner profile already records a different server claim status")
                return profile
            updated = dict(profile)
            updated["localState"] = "pending_confirmation"
            updated["serverClaimStatus"] = status
            updated["updatedAt"] = canonical_instant()
            updated = validate_profile(updated)
            self._write_profile_path(path, updated, replace=True)
            return updated

    def record_runner_id(self, challenge_id: str, runner_id: str) -> dict[str, object]:
        runner_id = validate_runner_id(runner_id)
        with self.locked():
            path = self.profile_path(challenge_id)
            profile = self._read_profile_path(path)
            if profile["runnerId"] is not None and profile["runnerId"] != runner_id:
                raise RunnerStateError("refusing to replace an already-recorded runner id")
            updated = dict(profile)
            updated["runnerId"] = runner_id
            updated["localState"] = "runner_id_recorded_unverified"
            updated["updatedAt"] = canonical_instant()
            updated = validate_profile(updated)
            self._write_profile_path(path, updated, replace=True)
            return updated

    def load_profile(self, challenge_id: str) -> dict[str, object]:
        with self.locked():
            return self._read_profile_path(self.profile_path(challenge_id))

    def load_key(self, profile: dict[str, object], passphrase: bytes):
        profile = validate_profile(profile)
        with self.locked():
            key_path = self.ensure() / profile["keyFile"]
            key = self._load_key_path(key_path, passphrase)
            _require_key_matches_profile(key, profile)
            return key

    def list_profiles(self) -> list[dict[str, object]]:
        with self.locked():
            profiles = []
            for path in sorted(self.ensure().glob("profile-*.json")):
                if _PROFILE_FILE_RE.fullmatch(path.name) is None:
                    continue
                profiles.append(self._read_profile_path(path))
            return profiles

    def forget(self, challenge_id: str) -> dict[str, object]:
        """Irreversibly delete one encrypted local key and its public profile."""
        with self.locked():
            profile_path = self.profile_path(challenge_id)
            profile = self._read_profile_path(profile_path)
            key_path = self.ensure() / profile["keyFile"]
            if key_path.exists():
                if key_path.is_symlink() or not key_path.is_file():
                    raise RunnerStateError("runner private-key path is unsafe")
                try:
                    key_path.unlink()
                except OSError as error:
                    raise RunnerStateError("runner private key could not be deleted") from error
            try:
                profile_path.unlink()
            except OSError as error:
                raise RunnerStateError("runner profile could not be deleted") from error
            return profile

    def _load_key_path(self, path: Path, passphrase: bytes):
        if path.is_symlink() or not path.is_file():
            raise RunnerStateError("runner private key is missing or unsafe")
        _require_private_file_mode(path)
        try:
            return load_private_key_file(path, passphrase)
        except KeyMaterialError as error:
            raise RunnerStateError(str(error)) from error

    def _read_profile_path(self, path: Path) -> dict[str, object]:
        if path.is_symlink() or not path.is_file():
            raise RunnerStateError("runner profile is missing or unsafe")
        _require_private_file_mode(path)
        try:
            with path.open("rb") as handle:
                raw = handle.read(MAX_PROFILE_BYTES + 1)
        except OSError as error:
            raise RunnerStateError("runner profile could not be read") from error
        if len(raw) > MAX_PROFILE_BYTES:
            raise RunnerStateError("runner profile exceeds the local size limit")
        try:
            profile = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
        except RunnerStateError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RunnerStateError("runner profile is not valid JSON") from error
        profile = validate_profile(profile)
        if path.name != f"profile-{profile['challengeId']}.json":
            raise RunnerStateError("runner profile filename does not match its challenge id")
        return profile

    def _write_profile_path(self, path: Path, profile: dict[str, object], *, replace: bool):
        profile = validate_profile(profile)
        if path.name != f"profile-{profile['challengeId']}.json":
            raise RunnerStateError("runner profile filename does not match its challenge id")
        if path.exists() and (path.is_symlink() or not path.is_file()):
            raise RunnerStateError("runner profile target is unsafe")
        if path.exists() and not replace:
            raise RunnerStateError("refusing to overwrite an existing runner profile")
        raw = (
            json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            + "\n"
        ).encode("utf-8")
        if len(raw) > MAX_PROFILE_BYTES:
            raise RunnerStateError("runner profile exceeds the local size limit")
        temporary = self.ensure() / f".{path.name}.{os.urandom(8).hex()}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        descriptor = None
        try:
            descriptor = os.open(temporary, flags, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            if not replace and path.exists():
                raise RunnerStateError("refusing to overwrite an existing runner profile")
            os.replace(temporary, path)
            _fsync_directory(self.ensure())
        except Exception:
            if descriptor is not None:
                os.close(descriptor)
            try:
                temporary.unlink()
            except OSError:
                pass
            raise


def validate_profile(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _PROFILE_KEYS:
        raise RunnerStateError("runner profile has an invalid exact schema")
    if value["schema"] != PROFILE_SCHEMA or value["protocolVersion"] != PAIRING_PROTOCOL:
        raise RunnerStateError("runner profile protocol is unsupported")
    challenge_id = validate_challenge_id(value["challengeId"])
    runner_id = value["runnerId"]
    if runner_id is not None:
        runner_id = validate_runner_id(runner_id)
    local_state = value["localState"]
    claim_status = value["serverClaimStatus"]
    if local_state not in PROFILE_STATES or claim_status not in CLAIM_STATUSES:
        raise RunnerStateError("runner profile state is invalid")
    if local_state == "prepared" and (claim_status != "not_confirmed" or runner_id is not None):
        raise RunnerStateError("prepared runner profile has contradictory state")
    if local_state == "pending_confirmation" and (claim_status == "not_confirmed" or runner_id is not None):
        raise RunnerStateError("pending runner profile has contradictory state")
    if local_state == "runner_id_recorded_unverified" and runner_id is None:
        raise RunnerStateError("runner-id profile has contradictory state")
    provider_id = value["providerId"]
    if provider_id not in PROVIDER_IDS:
        raise RunnerStateError("runner profile provider is unsupported")
    if value["connectionMode"] != connection_mode_for(provider_id):
        raise RunnerStateError("runner profile connection mode contradicts the provider catalog")
    harness_digest = value["harnessDigest"]
    if not isinstance(harness_digest, str) or _HEX_64_RE.fullmatch(harness_digest) is None:
        raise RunnerStateError("runner profile harness digest is invalid")
    public_key = value["publicKey"]
    if not isinstance(public_key, str) or re.fullmatch(r"[A-Za-z0-9_-]{43}", public_key) is None:
        raise RunnerStateError("runner profile public key is invalid")
    fingerprint = validate_fingerprint(value["fingerprint"])
    key_file = value["keyFile"]
    key_match = _KEY_FILE_RE.fullmatch(key_file) if isinstance(key_file, str) else None
    if key_match is None or key_match.group(1) != challenge_id:
        raise RunnerStateError("runner profile key filename is invalid")
    for field in ("createdAt", "updatedAt"):
        if not isinstance(value[field], str) or _INSTANT_RE.fullmatch(value[field]) is None:
            raise RunnerStateError(f"runner profile {field} is invalid")
    if value["localEvidenceClass"] != "local_ed25519_key_only":
        raise RunnerStateError("runner profile local evidence class is invalid")
    for field in (
        "accountApprovalAttested",
        "providerAccountAttested",
        "planEntitlementAttested",
        "billingRouteAttested",
        "modelAttested",
        "personAttested",
        "runtimeAttested",
        "harnessExecutionAttested",
        "matchExecutionAttested",
    ):
        if value[field] is not False:
            raise RunnerStateError(f"runner profile must keep {field} false")
    return {
        **value,
        "challengeId": challenge_id,
        "runnerId": runner_id,
        "endpointOrigin": validate_origin(value["endpointOrigin"]),
        "displayLabel": validate_display_label(value["displayLabel"]),
        "harnessId": validate_harness_id(value["harnessId"]),
        "harnessVersion": validate_harness_version(value["harnessVersion"]),
        "harnessDigest": harness_digest,
        "publicKey": public_key,
        "fingerprint": fingerprint,
    }


def _validated_candidate(
    *,
    endpoint_origin: str,
    provider_id: str,
    display_label: str,
    harness_id: str,
    harness_version: str,
    harness_digest: str,
) -> dict[str, str]:
    if provider_id not in PROVIDER_IDS:
        raise RunnerStateError("provider id is not in the closed AgentWars catalog")
    if not isinstance(harness_digest, str) or _HEX_64_RE.fullmatch(harness_digest) is None:
        raise RunnerStateError("harness digest is invalid")
    return {
        "endpointOrigin": validate_origin(endpoint_origin),
        "providerId": provider_id,
        "connectionMode": connection_mode_for(provider_id),
        "displayLabel": validate_display_label(display_label),
        "harnessId": validate_harness_id(harness_id),
        "harnessVersion": validate_harness_version(harness_version),
        "harnessDigest": harness_digest,
    }


def _require_same_candidate(profile: dict[str, object], candidate: dict[str, str]):
    for profile_field, candidate_field in (
        ("endpointOrigin", "endpointOrigin"),
        ("providerId", "providerId"),
        ("connectionMode", "connectionMode"),
        ("displayLabel", "displayLabel"),
        ("harnessId", "harnessId"),
        ("harnessVersion", "harnessVersion"),
        ("harnessDigest", "harnessDigest"),
    ):
        if profile[profile_field] != candidate[candidate_field]:
            raise RunnerStateError(
                f"retry candidate differs from the stored {profile_field}; refusing key rotation or metadata drift"
            )


def _require_key_matches_profile(key, profile: dict[str, object]):
    material = public_key_material(key)
    if material.public_key != profile["publicKey"] or material.fingerprint != profile["fingerprint"]:
        raise RunnerStateError("encrypted private key does not match the public runner profile")


def _require_private_file_mode(path: Path):
    if os.name == "nt":
        return
    try:
        info = path.lstat()
    except OSError as error:
        raise RunnerStateError("runner state file could not be inspected") from error
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise RunnerStateError("runner state file is accessible to another POSIX user")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise RunnerStateError("runner state file must be owned by the current user")


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RunnerStateError("runner profile contains duplicate JSON keys")
        result[key] = value
    return result


def _fsync_directory(path: Path):
    if os.name == "nt":
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)
