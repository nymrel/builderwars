"""Fail-closed admission for the shipped BuilderWars command-line tools.

This is an operator guard, not a sandbox. The arena engine still documents that
network egress, filesystem confinement, and CPU/memory limits are unenforced in
v1. The guard prevents the bundled CLIs from quietly treating arbitrary source
paths as if they had the same trust posture as the repository's own entrants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


class EntrantAdmissionError(ValueError):
    """An entrant path cannot be admitted under the requested CLI posture."""


def _resolved_file(value: str, *, working_directory: Path) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = working_directory / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise EntrantAdmissionError(
            f"entrant path does not resolve to an existing file: {value}"
        ) from exc
    if not resolved.is_file():
        raise EntrantAdmissionError(f"entrant path is not a file: {value}")
    return resolved


def classify_entry(
    value: str,
    *,
    repository_root: str | Path,
    working_directory: str | Path | None = None,
) -> dict[str, str]:
    """Classify one resolved path without trusting string prefixes or symlinks."""

    root = Path(repository_root).resolve(strict=True)
    cwd = Path.cwd() if working_directory is None else Path(working_directory)
    resolved = _resolved_file(value, working_directory=cwd.resolve())
    bundled_root = (root / "entrants").resolve(strict=True)
    try:
        relative = resolved.relative_to(bundled_root)
    except ValueError:
        return {
            "classification": "external-unconfined",
            "path": str(resolved),
        }
    return {
        "classification": "bundled-first-party",
        "path": str(resolved),
        "repository_path": str(Path("entrants") / relative),
    }


def require_entry_admission(
    values: Iterable[str],
    *,
    repository_root: str | Path,
    allow_unconfined: bool = False,
    working_directory: str | Path | None = None,
) -> tuple[dict[str, str], ...]:
    """Resolve every entrant and reject external paths unless explicitly armed."""

    records = tuple(
        classify_entry(
            value,
            repository_root=repository_root,
            working_directory=working_directory,
        )
        for value in values
    )
    external = [
        record["path"]
        for record in records
        if record["classification"] == "external-unconfined"
    ]
    if external and not allow_unconfined:
        rendered = ", ".join(external)
        raise EntrantAdmissionError(
            "external entrant paths are capability-unconfined in BuilderWars v1 "
            f"({rendered}). The shipped CLI refuses them by default because "
            "network egress, filesystem confinement, and CPU/memory limits are "
            "not enforced. Review the entrant and rerun with "
            "--allow-unconfined-entrants only on an owned host."
        )
    return records


def unconfined_warning(records: Iterable[dict[str, str]]) -> str | None:
    external = [
        record["path"]
        for record in records
        if record["classification"] == "external-unconfined"
    ]
    if not external:
        return None
    return (
        "WARNING: explicitly admitting capability-unconfined external entrant(s): "
        + ", ".join(external)
        + ". BuilderWars v1 does not block their network, filesystem, CPU, or memory access."
    )
