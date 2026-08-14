"""Engine self-identification.

The failure this exists to prevent: a competitor edits the referee, then reports
a clean result against their own edited rules. Hashing the engine's own source
into the transcript header means a result is only meaningful relative to a named
engine build, and a verifier says out loud whether it is running that build.

This does not stop someone editing the engine on their own machine. It stops
them doing it invisibly.
"""

import os

from .canonical import digest, file_digest

_SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache"}


def engine_files(root=None):
    """(relpath, sha256) for every .py in the arena package, sorted by path."""
    root = os.path.abspath(root or os.path.dirname(__file__))
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out.append([rel, file_digest(full)])
    return out


def engine_digest(root=None):
    """One hash covering the whole referee implementation."""
    return digest(engine_files(root))


def script_digest(cmd):
    """Hash the entrant's own script when the command line points at a real file.

    Binds "which harness played" to the result, which is the whole point of a
    contest whose thesis is that the harness is the variable.
    """
    for token in cmd:
        if isinstance(token, str) and os.path.isfile(token):
            ext = os.path.splitext(token)[1].lower()
            if ext in (".py", ".js", ".mjs", ".ts", ".sh", ".ps1", ".rb", ".exe"):
                return {"path": os.path.basename(token), "sha256": file_digest(token)}
    return None
