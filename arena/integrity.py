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
_HARNESS_EXTENSIONS = frozenset(
    {".py", ".js", ".mjs", ".ts", ".sh", ".ps1", ".rb", ".exe"}
)
_INTERPRETERS_BY_EXTENSION = {
    ".py": frozenset({"python", "python3", "py"}),
    ".js": frozenset({"node", "bun", "deno"}),
    ".mjs": frozenset({"node", "bun", "deno"}),
    ".ts": frozenset({"tsx", "ts-node", "bun", "deno"}),
    ".sh": frozenset({"sh", "bash"}),
    ".ps1": frozenset({"pwsh", "powershell"}),
    ".rb": frozenset({"ruby"}),
}
_KNOWN_INTERPRETERS = frozenset().union(*_INTERPRETERS_BY_EXTENSION.values())


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


def _command_name(value):
    name = os.path.basename(value).casefold()
    for suffix in (".exe", ".cmd", ".bat"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _script_record(token):
    if not isinstance(token, str) or not os.path.isfile(token):
        return None
    extension = os.path.splitext(token)[1].lower()
    if extension not in _HARNESS_EXTENSIONS:
        return None
    return {
        "path": os.path.basename(token),
        "sha256": file_digest(token),
        "extension": extension,
    }


def script_digest(cmd):
    """Hash the command's primary entrant harness, never its interpreter.

    Binds "which harness played" to the result, which is the whole point of a
    contest whose thesis is that the harness is the variable. Interpreter
    launches are intentionally strict: the harness must be exactly ``argv[1]``
    and the interpreter name must be allowlisted for that file type. We never
    scan later arguments because flags such as ``python -c`` would make the
    executable identity ambiguous.
    """
    if not isinstance(cmd, (list, tuple)) or not cmd:
        return None

    if len(cmd) >= 2 and isinstance(cmd[0], str):
        interpreted = _script_record(cmd[1])
        if interpreted is not None:
            allowed = _INTERPRETERS_BY_EXTENSION.get(
                interpreted.pop("extension"), frozenset()
            )
            if _command_name(cmd[0]) in allowed:
                return interpreted

    direct = _script_record(cmd[0])
    if direct is not None and _command_name(cmd[0]) not in _KNOWN_INTERPRETERS:
        direct.pop("extension")
        return direct
    return None
