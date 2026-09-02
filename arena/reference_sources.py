"""Engine-versioned source authority for reviewed local reference entrants.

``reference_reviewed_local_v1`` is a privileged truth label, not a convenient
way to launch arbitrary local code.  Every admitted harness must resolve to one
exact repository path and match the SHA-256 reviewed with this engine build.
The registry lives in Python so it is covered by ``engine_digest`` and can be
independently reconstructed by a verifier.

This is a preflight source check, not a capability sandbox or a claim that the
host cannot swap bytes after inspection.  Hosted untrusted code remains
unsupported, and customer-controlled local code uses the separate unreviewed
scope.
"""

from pathlib import Path
from types import MappingProxyType

from .canonical import digest, file_digest
from .integrity import primary_script_path


PROTOCOL = "builderwars/reviewed-reference-sources/1"
_REPO_ROOT = Path(__file__).resolve().parents[1]

REVIEWED_REFERENCE_SOURCES = MappingProxyType(
    {
        "entrants/backends.py": "aa43a848d8fc14716cafd412b6a692cfcf5db22675382dfacb70be3914b1a7f6",
        "entrants/cheater_harness.py": "bddfd9f92b34c7a5c48008a3f042ddce456478f805b96c75610573accb95f858",
        "entrants/fantasy_gm_harness.py": "d179cdf99d5c40f9414a0e74f35b550a357ed42e69a0e5539fbe5099ba146142",
        "entrants/fantasy_model_harness.py": "3e1cb9d461bf04f77113fed51f35915c2b32fae2085a1fba8ec817798735ece4",
        "entrants/fantasy_plan_harness.py": "58887c3c388c23e53a5d6faa5644e89c736b6d4c73e727a24b7b61316016eabf",
        "entrants/naive_harness.py": "e34af1369a8c083a16e20c4fb29515f6235da4e7f97be438fadeb3265b6d4d8a",
        "entrants/parsing.py": "cc8d39adea101f68c7b9ed11847d5fd65a294d289311c1400b35cbbf1f6aae33",
        "entrants/solver_harness.py": "d92b8970e35b27a2f5f456b044fc98b34ef47f68672e85ccf6532a76371d0626",
        "entrants/ten_fronts_forfeit_fixture.py": "26b4153fd1f94bb6970179f193465fd7e0e4b41a568ccb09ff1e4685666dd1df",
        "entrants/ten_fronts_model_harness.py": "3b7e372cc2e13e766f74fbe6af0ab25ad35c2a32f65ffd8bc7284f1b4dd5dcb4",
    }
)

REVIEWED_REFERENCE_ENTRYPOINTS = frozenset(
    {
        "entrants/cheater_harness.py",
        "entrants/fantasy_gm_harness.py",
        "entrants/fantasy_model_harness.py",
        "entrants/fantasy_plan_harness.py",
        "entrants/naive_harness.py",
        "entrants/solver_harness.py",
        "entrants/ten_fronts_forfeit_fixture.py",
        "entrants/ten_fronts_model_harness.py",
    }
)


class UnreviewedReferenceSource(ValueError):
    """A reference scope attempted to launch bytes outside its exact registry."""

    code = "UNREVIEWED_REFERENCE_SOURCE"

    def __init__(self, seat, reason):
        super().__init__(f"{self.code}: seat {seat}: {reason}")
        self.seat = seat
        self.reason = reason


def registry_digest():
    """Canonical identity of the ordered path/digest authority table."""

    return digest(
        [
            {"path": path, "sha256": sha256}
            for path, sha256 in sorted(REVIEWED_REFERENCE_SOURCES.items())
        ]
    )


def _verify_complete_registry():
    """Fail if any reviewed entrant source or shared dependency has drifted."""

    for relative, expected in sorted(REVIEWED_REFERENCE_SOURCES.items()):
        candidate = _REPO_ROOT / relative
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as error:
            raise UnreviewedReferenceSource(
                "registry", f"reviewed source {relative!r} is unavailable"
            ) from error
        if resolved != candidate.absolute():
            raise UnreviewedReferenceSource(
                "registry", f"reviewed source {relative!r} is not a regular direct path"
            )
        try:
            actual = file_digest(resolved)
        except OSError as error:
            raise UnreviewedReferenceSource(
                "registry", f"could not read reviewed source {relative!r}"
            ) from error
        if actual != expected:
            raise UnreviewedReferenceSource(
                "registry", f"reviewed registry digest mismatch for {relative!r}"
            )


def require_reviewed_reference_entrants(entrants):
    """Return transcript-safe bindings for an exact reviewed entrant pair.

    The caller must still perform normal manifest validation.  This function
    rejects missing/ambiguous commands, paths outside the repository, paths not
    in the registry, and byte drift.  It reads source only and must be invoked
    before any match-owned directory or entrant process exists.
    """

    if not isinstance(entrants, (list, tuple)):
        raise UnreviewedReferenceSource("?", "entrants must be an ordered array")

    _verify_complete_registry()
    bindings = []
    for seat, manifest in enumerate(entrants):
        if not isinstance(manifest, dict):
            raise UnreviewedReferenceSource(seat, "entrant manifest must be an object")
        source = primary_script_path(manifest.get("cmd"))
        if source is None:
            raise UnreviewedReferenceSource(
                seat, "command does not identify one exact supported harness"
            )
        try:
            resolved = Path(source).resolve(strict=True)
        except OSError as error:
            raise UnreviewedReferenceSource(
                seat, "harness disappeared during reviewed-source preflight"
            ) from error
        try:
            relative = resolved.relative_to(_REPO_ROOT).as_posix()
        except ValueError as error:
            raise UnreviewedReferenceSource(
                seat, "resolved harness is outside the reviewed repository root"
            ) from error
        expected = REVIEWED_REFERENCE_SOURCES.get(relative)
        if expected is None or relative not in REVIEWED_REFERENCE_ENTRYPOINTS:
            raise UnreviewedReferenceSource(
                seat, f"repository path {relative!r} is not an executable reviewed entrypoint"
            )
        try:
            actual = file_digest(resolved)
        except OSError as error:
            raise UnreviewedReferenceSource(
                seat, f"could not read reviewed source {relative!r}"
            ) from error
        if actual != expected:
            raise UnreviewedReferenceSource(
                seat, f"reviewed registry digest mismatch for {relative!r}"
            )
        bindings.append({"seat": seat, "path": relative, "sha256": actual})
    return bindings
