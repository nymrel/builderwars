#!/usr/bin/env python3
"""Generate `verify.py` — the whole verifier as one file a stranger can run.

Why this exists
---------------
The positioning is "re-run every match yourself." If checking a result needs a
clone, a virtualenv, an env file and a key, that claim is decorative. So the
verifier has to be one file and one command, fetched from nothing.

Why it embeds source rather than reimplementing it
--------------------------------------------------
A hand-written "lightweight verifier" is a second implementation of the rules,
and a second implementation drifts. When it drifts, the published verifier
blesses matches the referee would reject — which is precisely the failure the
whole arena exists to prevent.

So this embeds the `arena` package **verbatim, as raw bytes**, unpacks it to a
temp dir at run time, and imports the real thing. Byte-identical source means
the engine digest recorded in a transcript header matches the digest the
single-file verifier computes — and that equality is itself one of the checks a
reader sees. A drifted verifier cannot hide; it fails its own digest check.

Bytes, not text: the digest is over raw file bytes, so a CRLF/LF round-trip
through a text-mode read would change every hash and break the digest check on
Windows. Everything here is binary in and binary out.

Regenerate after ANY change under `arena/`:

    python bin/build_verifier.py            # writes verify.py
    python bin/build_verifier.py --check     # conformance: same verdicts as the package
"""

import argparse
import base64
import binascii
import glob
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARENA = os.path.join(ROOT, "arena")
OUT = os.path.join(ROOT, "verify.py")
SNAPSHOT_DIR = os.path.join(ROOT, "bin", "verifier_snapshots")

DEFAULT_BASE = "https://nymrel.com/builderwars"

_MAX_SOURCE_FILES = 256
_MAX_SOURCE_BYTES = 2 * 1024 * 1024
_MAX_SOURCE_SET_BYTES = 16 * 1024 * 1024
_MAX_SNAPSHOT_BYTES = 24 * 1024 * 1024
_MAX_SOURCE_PATH_BYTES = 240
_SOURCE_PATH_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/"
)
_REQUIRED_ENGINE_SOURCES = frozenset(
    {"__init__.py", "canonical.py", "integrity.py", "replay.py"}
)
_WINDOWS_DEVICE_STEMS = frozenset(
    (
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    )
)


class SnapshotError(ValueError):
    """A preserved verifier source set failed its custody contract."""


class _DuplicateSnapshotKey(SnapshotError):
    pass


def _object_without_duplicate_snapshot_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateSnapshotKey("duplicate object key")
        value[key] = item
    return value


def _valid_digest(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(char in "0123456789abcdef" for char in value)
    )


def _validated_base_url(value):
    if (
        not isinstance(value, str)
        or not (1 <= len(value) <= 2048)
        or not value.startswith(("https://", "http://"))
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
        or any(char in value for char in ("\\", '"', "'"))
    ):
        raise ValueError("verifier base URL must be one bounded HTTP(S) URL")
    return value


def _validate_source_path(rel):
    if not isinstance(rel, str):
        raise SnapshotError("source path must be a string")
    try:
        encoded = rel.encode("ascii")
    except UnicodeEncodeError as error:
        raise SnapshotError("source path must be ASCII") from error
    parts = rel.split("/")
    if (
        not encoded
        or len(encoded) > _MAX_SOURCE_PATH_BYTES
        or rel.startswith("/")
        or "\\" in rel
        or ":" in rel
        or any(char not in _SOURCE_PATH_CHARS for char in rel)
        or any(not part or part in (".", "..") for part in parts)
        or any(part != part.rstrip(". ") for part in parts)
        or any(part.split(".", 1)[0].upper() in _WINDOWS_DEVICE_STEMS for part in parts)
        or any(len(part.encode("ascii")) > 100 for part in parts)
        or not parts[-1].endswith(".py")
    ):
        raise SnapshotError("source path is not a canonical package-relative Python path")
    return parts


def _engine_walk_order(paths):
    """Reconstruct integrity.engine_files' files-before-subdirs walk order."""
    root = {"files": {}, "dirs": {}}
    for rel in paths:
        parts = _validate_source_path(rel)
        node = root
        for part in parts[:-1]:
            folded = part.casefold()
            if folded in node["files"]:
                raise SnapshotError("source path collides with a file on case-insensitive hosts")
            entry = node["dirs"].setdefault(folded, (part, {"files": {}, "dirs": {}}))
            if entry[0] != part:
                raise SnapshotError("source paths collide on case-insensitive hosts")
            node = entry[1]
        name = parts[-1]
        folded = name.casefold()
        if folded in node["dirs"] or folded in node["files"]:
            raise SnapshotError("source paths collide on case-insensitive hosts")
        node["files"][folded] = (name, rel)

    ordered = []

    def walk(node):
        for _folded, (_name, rel) in sorted(
            node["files"].items(), key=lambda row: row[1][0]
        ):
            ordered.append(rel)
        for _folded, (_name, child) in sorted(
            node["dirs"].items(), key=lambda row: row[1][0]
        ):
            walk(child)

    walk(root)
    return ordered


def _decode_source_map(sources):
    if not isinstance(sources, dict) or not (1 <= len(sources) <= _MAX_SOURCE_FILES):
        raise SnapshotError("source map size is outside the supported bounds")
    decoded = {}
    total = 0
    for rel, value in sources.items():
        _validate_source_path(rel)
        if not isinstance(value, str) or len(value) > ((_MAX_SOURCE_BYTES + 2) // 3) * 4:
            raise SnapshotError("encoded source is not a bounded string")
        try:
            raw = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as error:
            raise SnapshotError("source is not strict base64") from error
        if base64.b64encode(raw).decode("ascii") != value:
            raise SnapshotError("source base64 is not canonical")
        if len(raw) > _MAX_SOURCE_BYTES:
            raise SnapshotError("source exceeds the per-file byte limit")
        total += len(raw)
        if total > _MAX_SOURCE_SET_BYTES:
            raise SnapshotError("source set exceeds the total byte limit")
        decoded[rel] = raw
    if not _REQUIRED_ENGINE_SOURCES.issubset(decoded):
        raise SnapshotError("source set is missing required engine modules")
    return [(rel, decoded[rel]) for rel in _engine_walk_order(decoded)]


def _load_snapshot(path):
    try:
        file_stat = os.lstat(path)
    except OSError as error:
        raise SnapshotError("snapshot metadata is unavailable") from error
    if (
        not stat.S_ISREG(file_stat.st_mode)
        or os.path.islink(path)
    ):
        raise SnapshotError("snapshot must be one ordinary, non-symlink file")
    if file_stat.st_size > _MAX_SNAPSHOT_BYTES:
        raise SnapshotError("snapshot exceeds the byte limit")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(
                fh, object_pairs_hook=_object_without_duplicate_snapshot_keys
            )
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, SnapshotError):
            raise
        raise SnapshotError(f"snapshot JSON is invalid ({error.__class__.__name__})") from error
    if not isinstance(payload, dict) or set(payload) != {"engineDigest", "sources"}:
        raise SnapshotError("snapshot must contain exactly engineDigest and sources")
    engine_digest = payload["engineDigest"]
    if not _valid_digest(engine_digest):
        raise SnapshotError("engineDigest must be 64-char lowercase hex")
    if os.path.basename(path) != f"{engine_digest}.json":
        raise SnapshotError("snapshot filename must match engineDigest")
    files = _decode_source_map(payload["sources"])
    if digest_for(files) != engine_digest:
        raise SnapshotError("snapshot sources do not bind to engineDigest")
    return engine_digest, encode_sources(files)


def collect():
    """(relpath, raw bytes) for every .py under arena/.

    Order matters and must match `integrity.engine_files` exactly: the engine
    digest is a hash of the ordered [path, hash] list, so re-sorting the walk
    (which puts `games/__init__.py` before `integrity.py`) yields a different
    digest for identical bytes. Delegating to engine_files rather than
    re-implementing the walk is what keeps the two from drifting apart.
    """
    from arena.integrity import engine_files  # the referee's own ordering

    out = []
    for rel, _ in engine_files(ARENA):
        with open(os.path.join(ARENA, *rel.split("/")), "rb") as fh:
            out.append((rel, fh.read()))
    return out


def digest_for(files):
    """Compute the exact digest `arena.integrity.engine_digest` records."""
    from arena.canonical import digest  # noqa: E402

    pairs = [[rel, hashlib.sha256(raw).hexdigest()] for rel, raw in files]
    return digest(pairs)


def encode_sources(files):
    return {rel: base64.b64encode(raw).decode("ascii") for rel, raw in files}


def snapshot_current():
    """Preserve the current referee bytes before the package changes.

    A result is bound to its engine digest. Keeping one byte-exact source set per
    published digest lets the latest `verify.py` continue checking old matches
    after a new game or referee version ships.
    """
    files = collect()
    engine_digest = digest_for(files)
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    path = os.path.join(SNAPSHOT_DIR, f"{engine_digest}.json")
    payload = {
        "engineDigest": engine_digest,
        "sources": encode_sources(files),
    }
    if os.path.exists(path):
        try:
            existing_digest, existing_sources = _load_snapshot(path)
        except SnapshotError as error:
            raise SystemExit(
                f"invalid existing verifier snapshot {engine_digest}: {error}"
            ) from error
        if existing_digest != engine_digest or existing_sources != payload["sources"]:
            raise SystemExit(f"snapshot collision for {engine_digest}")
        print(f"snapshot already current: {os.path.relpath(path, ROOT)}")
        return path
    serialized = (
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    fd, staged = tempfile.mkstemp(prefix=".verifier-snapshot-", suffix=".tmp", dir=SNAPSHOT_DIR)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(serialized)
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.link(staged, path)
        except FileExistsError:
            try:
                existing_digest, existing_sources = _load_snapshot(path)
            except SnapshotError as error:
                raise SystemExit(
                    f"invalid concurrently-created verifier snapshot {engine_digest}: {error}"
                ) from error
            if existing_digest != engine_digest or existing_sources != payload["sources"]:
                raise SystemExit(f"snapshot collision for {engine_digest}")
    finally:
        try:
            os.unlink(staged)
        except FileNotFoundError:
            pass
    print(f"snapshotted {len(files)} files -> {os.path.relpath(path, ROOT)}")
    return path


def source_sets(current_files):
    """Return every preserved engine plus the current one, keyed by digest."""
    sets = {}
    if os.path.isdir(SNAPSHOT_DIR):
        for path in sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json"))):
            try:
                engine_digest, sources = _load_snapshot(path)
            except SnapshotError as error:
                raise SystemExit(
                    f"invalid verifier snapshot {os.path.basename(path)}: {error}"
                ) from error
            if engine_digest in sets and sets[engine_digest] != sources:
                raise SystemExit(f"duplicate verifier digest with different bytes: {engine_digest}")
            sets[engine_digest] = sources
    current_digest = digest_for(current_files)
    current_sources = encode_sources(_decode_source_map(encode_sources(current_files)))
    if current_digest in sets and sets[current_digest] != current_sources:
        raise SystemExit(f"current verifier digest collides with preserved bytes: {current_digest}")
    sets[current_digest] = current_sources
    return sets


def render_source_sets(sets):
    """Readable Python literal with base64 split into reviewable 88-char lines."""
    lines = ["{"]
    for engine_digest, sources in sorted(sets.items()):
        lines.append(f'    "{engine_digest}": {{')
        for rel, b64 in sorted(sources.items()):
            chunks = [b64[i:i + 88] for i in range(0, len(b64), 88)] or [""]
            lines.append(f'        "{rel}":')
            for index, chunk in enumerate(chunks):
                comma = "," if index == len(chunks) - 1 else ""
                lines.append(f'            "{chunk}"{comma}')
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


HEADER = '''#!/usr/bin/env python3
"""BuilderWars — verify one match, from nothing.

    python verify.py <match-id>        fetches the match and checks it
    python verify.py path/to.jsonl     checks a transcript you already have
    python verify.py <match-id> --json full report as JSON

Exit code 0 means PASS. Unsigned legacy receipts need only stock Python 3.
Signed Agent Passport receipts additionally require BuilderWars' declared
optional `cryptography` dependency; absence fails closed and never downgrades
the receipt to legacy identity.

This file contains the referee's own source, embedded byte-for-byte. It unpacks
to a temp directory, runs the real engine, and deletes it again. That is on
purpose: a separate "lightweight" verifier would be a second implementation of
the rules, and when it drifted it would start blessing matches the referee would
reject. Because the source here is byte-identical, the engine digest recorded in
the transcript must equal the digest computed here — and you see that comparison
in the output as `engine_digest`. If someone tampers with this file, that check
is what fails.

Read it before you run it. It is meant to be read.
"""

import argparse
import atexit
import base64
import binascii
import json
import os
import shutil
import sys
import tempfile
import urllib.request

BASE = os.environ.get("BUILDERWARS_BASE", {base_literal})

# engine digest -> (relpath -> base64 bytes). Historical referee builds remain
# embedded so a new game cannot strand already-published match receipts.
SOURCE_SETS = {source_sets}
DEFAULT_ENGINE_DIGEST = "{engine_digest}"

_MAX_SOURCE_FILES = 256
_MAX_SOURCE_BYTES = 2 * 1024 * 1024
_MAX_SOURCE_SET_BYTES = 16 * 1024 * 1024
_MAX_SOURCE_PATH_BYTES = 240
_SOURCE_PATH_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/"
)
_REQUIRED_ENGINE_SOURCES = frozenset(
    ("__init__.py", "canonical.py", "integrity.py", "replay.py")
)
_WINDOWS_DEVICE_STEMS = frozenset(
    (
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    )
)
_MAX_TRANSCRIPT_BYTES = 64 * 1024 * 1024
_MAX_PREFLIGHT_NODES = 1_000_000


def _decode_sources(sources):
    if not isinstance(sources, dict) or not (1 <= len(sources) <= _MAX_SOURCE_FILES):
        raise ValueError("embedded source map size is outside the supported bounds")
    decoded = []
    seen = set()
    total = 0
    for rel, value in sources.items():
        if not isinstance(rel, str):
            raise ValueError("embedded source path must be a string")
        try:
            encoded = rel.encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError("embedded source path must be ASCII") from error
        parts = rel.split("/")
        folded = rel.casefold()
        if (
            not encoded
            or len(encoded) > _MAX_SOURCE_PATH_BYTES
            or rel.startswith("/")
            or "\\\\" in rel
            or ":" in rel
            or folded in seen
            or any(char not in _SOURCE_PATH_CHARS for char in rel)
            or any(not part or part in (".", "..") for part in parts)
            or any(part != part.rstrip(". ") for part in parts)
            or any(part.split(".", 1)[0].upper() in _WINDOWS_DEVICE_STEMS for part in parts)
            or any(len(part.encode("ascii")) > 100 for part in parts)
            or not parts[-1].endswith(".py")
        ):
            raise ValueError("embedded source path is not canonical and package-relative")
        seen.add(folded)
        if not isinstance(value, str) or len(value) > ((_MAX_SOURCE_BYTES + 2) // 3) * 4:
            raise ValueError("embedded source is not a bounded string")
        try:
            raw = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("embedded source is not strict base64") from error
        if base64.b64encode(raw).decode("ascii") != value or len(raw) > _MAX_SOURCE_BYTES:
            raise ValueError("embedded source bytes are not canonical or bounded")
        total += len(raw)
        if total > _MAX_SOURCE_SET_BYTES:
            raise ValueError("embedded source set exceeds the total byte limit")
        decoded.append((rel, parts, raw))
    if not _REQUIRED_ENGINE_SOURCES.issubset(sources):
        raise ValueError("embedded source set is missing required engine modules")
    folded_paths = {{rel.casefold() for rel in sources}}
    for rel, _parts, _raw in decoded:
        parts = rel.casefold().split("/")
        if any("/".join(parts[:index]) in folded_paths for index in range(1, len(parts))):
            raise ValueError("embedded source path collides with a file prefix")
    return decoded


def _unpack(sources):
    decoded = _decode_sources(sources)
    root = tempfile.mkdtemp(prefix="builderwars-verify-")
    atexit.register(shutil.rmtree, root, True)
    pkg = os.path.abspath(os.path.join(root, "arena"))
    for _rel, parts, raw in decoded:
        dest = os.path.abspath(os.path.join(pkg, *parts))
        if os.path.commonpath((pkg, dest)) != pkg:
            raise ValueError("embedded source path escapes the package root")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:          # binary: hashes are over raw bytes
            fh.write(raw)
    sys.path.insert(0, root)
    return root


class _DuplicateKey(ValueError):
    pass


def _object_without_duplicate_keys(pairs):
    obj = {{}}
    for key, value in pairs:
        if key in obj:
            raise _DuplicateKey(f"duplicate object key {{key!r}}")
        obj[key] = value
    return obj


def _contains_object_key(value, needle):
    """Bounded iterative key scan used only for fail-closed trust preflight."""
    pending = [value]
    visited = 0
    while pending:
        current = pending.pop()
        visited += 1
        if visited > _MAX_PREFLIGHT_NODES:
            raise ValueError("transcript preflight exceeds the object-node limit")
        if isinstance(current, dict):
            if needle in current:
                return True
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
    return False


def _inspect_transcript(path):
    """Return (engine digest, signed-block-present, preflight error).

    This wrapper-level scan applies even when an old embedded snapshot predates
    duplicate-key and passport handling. A signed block can never be silently
    interpreted by a legacy-only snapshot.
    """
    signed = False
    try:
        header = None
        header_positions = []
        record_count = 0
        row_shape_error = None
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line, object_pairs_hook=_object_without_duplicate_keys)
                signed = signed or _contains_object_key(row, "agent_passport")
                if not isinstance(row, dict):
                    if row_shape_error is None:
                        row_shape_error = "transcript preflight: every record must be an object"
                elif row.get("kind") == "header":
                    header_positions.append(record_count)
                    if header is None:
                        header = row
                record_count += 1
        if row_shape_error is not None:
            return None, signed, row_shape_error
        if header_positions != [0] or not isinstance(header, dict):
            return None, signed, "transcript preflight: transcript must open with exactly one header"
        body = header.get("body")
        if not isinstance(body, dict):
            return None, signed, "transcript preflight: header body must be an object"
        engine = body.get("engine")
        recorded_digest = engine.get("digest") if isinstance(engine, dict) else None
        entrants = body.get("entrants")
        entrants_are_canonical = (
            isinstance(entrants, list)
            and len(entrants) == 2
            and all(isinstance(row, dict) for row in entrants)
            and all(type(row.get("seat")) is int for row in entrants)
            and [row["seat"] for row in entrants] == [0, 1]
        )
        if not entrants_are_canonical:
            return recorded_digest, signed, (
                "transcript preflight: header must contain exactly ordered entrant seats 0 and 1"
            )
        canonical_signed = any(
            isinstance(row, dict) and "agent_passport" in row for row in entrants
        )
        if signed != canonical_signed:
            return recorded_digest, signed, (
                "transcript preflight: agent_passport appears outside canonical entrant rows"
            )
        return recorded_digest, signed, None
    except Exception as error:
        return None, signed, f"transcript preflight: {{error.__class__.__name__}}: {{error}}"


def _fetch(arg):
    """A local path is used as-is. Anything else is treated as a match id or URL."""
    if os.path.exists(arg):
        if not os.path.isfile(arg) or os.path.getsize(arg) > _MAX_TRANSCRIPT_BYTES:
            raise SystemExit("local transcript is not one bounded regular file")
        return arg, None
    url = arg if arg.startswith(("http://", "https://")) else f"{{BASE}}/m/{{arg}}.jsonl"
    tmp = tempfile.NamedTemporaryFile(prefix="builderwars-", suffix=".jsonl", delete=False)
    atexit.register(os.unlink, tmp.name)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = resp.read(_MAX_TRANSCRIPT_BYTES + 1)
            if len(payload) > _MAX_TRANSCRIPT_BYTES:
                raise ValueError("transcript exceeds 64 MiB")
            tmp.write(payload)
    except Exception as e:
        tmp.close()
        sys.stderr.write(f"could not fetch {{url}}\\n  {{e.__class__.__name__}}: {{e}}\\n")
        raise SystemExit(2)
    tmp.close()
    # Return the URL actually fetched. Re-deriving it for display would print a
    # BASE-prefixed path even when the caller passed a full URL.
    return tmp.name, url


def main():
    ap = argparse.ArgumentParser(description="Verify one BuilderWars match.")
    ap.add_argument("match", help="match id, URL, or path to a transcript")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    path, source_url = _fetch(args.match)
    recorded_digest, signed_present, transcript_preflight_error = _inspect_transcript(path)
    selected_digest = (
        recorded_digest
        if isinstance(recorded_digest, str) and recorded_digest in SOURCE_SETS
        else DEFAULT_ENGINE_DIGEST
    )
    signed_verifier_capable = "passport.py" in SOURCE_SETS[selected_digest]
    _unpack(SOURCE_SETS[selected_digest])
    from arena.replay import verify          # the digest-matched referee verifier

    report = verify(path)
    report["verifier_engine_selected"] = selected_digest
    report["verifier_snapshot_match"] = recorded_digest == selected_digest
    report["replay_verdict"] = report.get("verdict")
    report["signed_passport_present"] = signed_present
    report["signed_verifier_capable"] = signed_verifier_capable
    report["transcript_preflight_error"] = transcript_preflight_error
    effective_pass = (
        report.get("replay_verdict") == "PASS"
        and report.get("engine_digest_match") is True
        and report.get("verifier_snapshot_match") is True
        and transcript_preflight_error is None
        and (not signed_present or signed_verifier_capable)
    )
    report["effective_verdict"] = "PASS" if effective_pass else "FAIL"
    effective_errors = list(report.get("errors") or [])
    if report.get("engine_digest_match") is not True:
        effective_errors.append("effective_verdict: referee engine digest does not match")
    if report.get("verifier_snapshot_match") is not True:
        effective_errors.append("effective_verdict: exact embedded verifier snapshot is unavailable")
    if transcript_preflight_error is not None:
        effective_errors.append(transcript_preflight_error)
    if signed_present and not signed_verifier_capable:
        effective_errors.append(
            "unsupported_verifier_for_signed: selected engine snapshot predates "
            "in-engine Agent Passport verification"
        )
    report["effective_errors"] = effective_errors

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if effective_pass else 1

    print(f"match      : {{report.get('match_id')}}  game={{report.get('game')}} seed={{report.get('seed')}}")
    if source_url:
        print(f"source     : {{source_url}}")
    print(f"chain head : {{report.get('chain_head', '-')}}")
    print()
    for c in report["checks"]:
        mark = "PASS" if c["ok"] else "FAIL"
        line = f"  [{{mark}}] {{c['check']}}"
        if c.get("detail"):
            line += f" - {{c['detail']}}"
        print(line)
    print()
    if report.get("recorded"):
        print(f"  recorded   : {{json.dumps(report['recorded'])}}")
        print(f"  recomputed : {{json.dumps(report['recomputed'])}}")
        print()
    print(f"REPLAY VERDICT: {{report['replay_verdict']}}")
    print(f"VERDICT: {{report['effective_verdict']}}")
    if effective_pass:
        print("\\nthis proves:")
        for p in report["proves"]:
            print(f"  + {{p}}")
        print("\\nthis does NOT prove:")
        for p in report["does_not_prove"]:
            print(f"  - {{p}}")
    else:
        for e in report["effective_errors"]:
            print(f"  ! {{e}}")
    return 0 if effective_pass else 1


if __name__ == "__main__":
    sys.exit(main())
'''


def build(base_url):
    base_url = _validated_base_url(base_url)
    files = collect()
    engine_digest = digest_for(files)
    sets = source_sets(files)

    src = HEADER.format(
        base_literal=repr(base_url),
        source_sets=render_source_sets(sets),
        engine_digest=engine_digest,
    )
    fd, staged = tempfile.mkstemp(prefix=".verify-", suffix=".py", dir=ROOT)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(staged, OUT)
    finally:
        try:
            os.unlink(staged)
        except FileNotFoundError:
            pass
    return files, engine_digest, len(sets)


def verdict_with_sources(sources, transcript):
    """Run one preserved referee in a fresh interpreter and return its verdict."""
    decoded = _decode_source_map(sources)
    with tempfile.TemporaryDirectory(prefix="builderwars-check-") as root:
        package = os.path.abspath(os.path.join(root, "arena"))
        for rel, raw in decoded:
            path = os.path.abspath(os.path.join(package, *rel.split("/")))
            if os.path.commonpath((package, path)) != package:
                raise SnapshotError("source path escapes the package root")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(raw)
        env = dict(os.environ)
        env["PYTHONPATH"] = root
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json,sys; from arena.replay import verify; "
                "print(json.dumps(verify(sys.argv[1])))",
                os.path.abspath(transcript),
            ],
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            return json.loads(proc.stdout.decode("utf-8", "replace"))["verdict"]
        except Exception:
            return f"CRASH({proc.stderr.decode('utf-8', 'replace')[:120]})"


def check_snapshot_guards():
    """Exercise the preserved-source parser with release-material attacks."""
    files = collect()
    engine_digest = digest_for(files)
    sources = encode_sources(files)
    payload = {"engineDigest": engine_digest, "sources": sources}
    checks = 0

    with tempfile.TemporaryDirectory(prefix="builderwars-snapshot-guards-") as root:
        path = os.path.join(root, f"{engine_digest}.json")

        def write_payload(value):
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(value, fh, sort_keys=True, separators=(",", ":"))
                fh.write("\n")

        def reject(label, *, value=None, raw=None, target=path):
            nonlocal checks
            if raw is not None:
                with open(target, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(raw)
            else:
                write_payload(value)
            try:
                _load_snapshot(target)
            except SnapshotError:
                checks += 1
                return
            raise AssertionError(f"snapshot guard accepted {label}")

        write_payload(payload)
        loaded_digest, loaded_sources = _load_snapshot(path)
        if loaded_digest != engine_digest or loaded_sources != sources:
            raise AssertionError("valid snapshot did not round-trip exactly")
        checks += 1

        reject(
            "duplicate keys",
            raw=(
                '{"engineDigest":"' + engine_digest + '",'
                '"engineDigest":"' + engine_digest + '","sources":{}}\n'
            ),
        )

        for label, hostile_path in (
            ("forward traversal", "../../escape.py"),
            ("backslash traversal", "..\\..\\escape.py"),
            ("drive path", "C:/escape.py"),
            ("trailing-dot directory", "games./escape.py"),
            ("reserved Windows device", "CON.py"),
        ):
            hostile_sources = dict(sources)
            hostile_sources[hostile_path] = base64.b64encode(b"pass\n").decode("ascii")
            reject(label, value={"engineDigest": engine_digest, "sources": hostile_sources})

        malformed_b64 = dict(sources)
        malformed_b64["canonical.py"] = "***"
        reject(
            "non-base64 source",
            value={"engineDigest": engine_digest, "sources": malformed_b64},
        )

        case_collision = dict(sources)
        case_collision["CANONICAL.py"] = case_collision["canonical.py"]
        reject(
            "case-insensitive source collision",
            value={"engineDigest": engine_digest, "sources": case_collision},
        )

        wrong_digest = "0" * 64
        wrong_path = os.path.join(root, f"{wrong_digest}.json")
        with open(wrong_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(
                {"engineDigest": wrong_digest, "sources": sources},
                fh,
                sort_keys=True,
                separators=(",", ":"),
            )
            fh.write("\n")
        with open(wrong_path, "r", encoding="utf-8") as fh:
            wrong_raw = fh.read()
        reject(
            "digest-content mismatch",
            raw=wrong_raw,
            target=wrong_path,
        )

        local_base = "http://127.0.0.1:8080/builderwars"
        if _validated_base_url(local_base) != local_base:
            raise AssertionError("bounded local HTTP verifier base was not retained")
        checks += 1
        for hostile_base in (
            "file:///private/transcript",
            'https://example.invalid/";raise RuntimeError()',
            "https://example.invalid/\nINJECT",
        ):
            try:
                _validated_base_url(hostile_base)
            except ValueError:
                checks += 1
            else:
                raise AssertionError("verifier base URL guard accepted code-shaped input")

    return checks


def check_runtime_unpack_guard():
    """Prove a tampered embedded path cannot write outside the temp package."""
    files = collect()
    engine_digest = digest_for(files)
    sources = encode_sources(files)
    handle = tempfile.NamedTemporaryFile(
        prefix="builderwars-verifier-escape-",
        suffix=".py",
        dir=tempfile.gettempdir(),
        delete=False,
    )
    escape_path = handle.name
    handle.close()
    os.unlink(escape_path)
    hostile = dict(sources)
    hostile["../../" + os.path.basename(escape_path)] = base64.b64encode(
        b"raise RuntimeError('escaped verifier source')\n"
    ).decode("ascii")
    script = HEADER.format(
        base_literal=repr(DEFAULT_BASE),
        source_sets=render_source_sets({engine_digest: hostile}),
        engine_digest=engine_digest,
    )
    try:
        with tempfile.TemporaryDirectory(prefix="builderwars-unpack-guard-") as root:
            verifier = os.path.join(root, "verify-hostile.py")
            transcript = os.path.join(root, "empty.jsonl")
            with open(verifier, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(script)
            with open(transcript, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("{}\n")
            proc = subprocess.run(
                [sys.executable, verifier, transcript, "--json"],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
            )
        escaped = os.path.exists(escape_path)
        marker = b"embedded source path is not canonical and package-relative"
        if proc.returncode == 0 or escaped or marker not in proc.stderr:
            raise AssertionError(
                "standalone verifier path guard did not fail at the intended boundary"
            )
    finally:
        try:
            os.unlink(escape_path)
        except FileNotFoundError:
            pass
    prefix_hostile = dict(sources)
    prefix_hostile["prefix.py"] = base64.b64encode(b"pass\n").decode("ascii")
    prefix_hostile["prefix.py/child.py"] = base64.b64encode(b"pass\n").decode("ascii")
    prefix_script = HEADER.format(
        base_literal=repr(DEFAULT_BASE),
        source_sets=render_source_sets({engine_digest: prefix_hostile}),
        engine_digest=engine_digest,
    )
    with tempfile.TemporaryDirectory(prefix="builderwars-prefix-guard-") as root:
        verifier = os.path.join(root, "verify-hostile.py")
        transcript = os.path.join(root, "empty.jsonl")
        with open(verifier, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(prefix_script)
        with open(transcript, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("{}\n")
        proc = subprocess.run(
            [sys.executable, verifier, transcript, "--json"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
    if (
        proc.returncode == 0
        or b"embedded source path collides with a file prefix" not in proc.stderr
    ):
        raise AssertionError("standalone verifier file-prefix guard was not reached")

    trailing_hostile = dict(sources)
    trailing_hostile["games./escape.py"] = base64.b64encode(b"pass\n").decode("ascii")
    trailing_script = HEADER.format(
        base_literal=repr(DEFAULT_BASE),
        source_sets=render_source_sets({engine_digest: trailing_hostile}),
        engine_digest=engine_digest,
    )
    with tempfile.TemporaryDirectory(prefix="builderwars-trailing-dot-guard-") as root:
        verifier = os.path.join(root, "verify-hostile.py")
        transcript = os.path.join(root, "empty.jsonl")
        with open(verifier, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(trailing_script)
        with open(transcript, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("{}\n")
        proc = subprocess.run(
            [sys.executable, verifier, transcript, "--json"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
    if (
        proc.returncode == 0
        or b"embedded source path is not canonical and package-relative" not in proc.stderr
    ):
        raise AssertionError("standalone verifier trailing-dot guard was not reached")
    return 3


def check_runtime_transcript_preflight():
    """Attack wrapper trust labels independently of the selected referee version."""
    engine_digest = digest_for(collect())
    base_header = {
        "kind": "header",
        "body": {
            "engine": {"digest": engine_digest},
            "entrants": [{"seat": 0}, {"seat": 1}],
        },
    }

    def inspect(records):
        with tempfile.TemporaryDirectory(prefix="builderwars-preflight-") as root:
            transcript = os.path.join(root, "attack.jsonl")
            with open(transcript, "w", encoding="utf-8", newline="\n") as fh:
                for record in records:
                    fh.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            proc = subprocess.run(
                [sys.executable, OUT, transcript, "--json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
            )
        try:
            report = json.loads(proc.stdout.decode("utf-8"))
        except Exception as error:
            raise AssertionError(
                f"standalone verifier preflight did not emit JSON: {proc.stderr[:200]!r}"
            ) from error
        return proc, report

    proc, report = inspect([base_header])
    if report.get("transcript_preflight_error") is not None:
        raise AssertionError("canonical unsigned header failed wrapper preflight")
    if report.get("signed_passport_present") is not False:
        raise AssertionError("canonical unsigned header was mislabeled signed")

    signed_header = json.loads(json.dumps(base_header))
    signed_header["body"]["entrants"][0]["agent_passport"] = {"schema": "attack"}
    proc, report = inspect([signed_header])
    if report.get("transcript_preflight_error") is not None:
        raise AssertionError("canonical signed header failed wrapper structure preflight")
    if report.get("signed_passport_present") is not True:
        raise AssertionError("canonical signed header was mislabeled unsigned")

    duplicate = json.loads(json.dumps(base_header))
    duplicate["body"]["entrants"][1]["agent_passport"] = {"schema": "attack"}
    proc, report = inspect([base_header, duplicate])
    if (
        proc.returncode == 0
        or report.get("effective_verdict") != "FAIL"
        or report.get("signed_passport_present") is not True
        or "exactly one header" not in str(report.get("transcript_preflight_error"))
    ):
        raise AssertionError("duplicate signed header did not fail closed in wrapper preflight")

    mapped_entrants = json.loads(json.dumps(base_header))
    mapped_entrants["body"]["entrants"] = {
        "0": {"seat": 0, "agent_passport": {"schema": "attack"}},
        "1": {"seat": 1},
    }
    proc, report = inspect([mapped_entrants])
    if (
        proc.returncode == 0
        or report.get("effective_verdict") != "FAIL"
        or report.get("signed_passport_present") is not True
        or "ordered entrant seats" not in str(report.get("transcript_preflight_error"))
    ):
        raise AssertionError("mapped signed entrants did not fail closed in wrapper preflight")

    misplaced = json.loads(json.dumps(base_header))
    misplaced["body"]["metadata"] = {"agent_passport": {"schema": "attack"}}
    proc, report = inspect([misplaced])
    if (
        proc.returncode == 0
        or report.get("effective_verdict") != "FAIL"
        or report.get("signed_passport_present") is not True
        or "outside canonical entrant rows" not in str(report.get("transcript_preflight_error"))
    ):
        raise AssertionError("misplaced passport block did not fail closed in wrapper preflight")
    return 5


def check():
    """Conformance: the single file must agree with the package on every transcript.

    A verifier that disagrees with the referee is worse than no verifier, so this
    compares verdicts one by one rather than trusting that embedding "obviously"
    preserves behaviour.
    """
    sys.path.insert(0, ROOT)
    from arena.integrity import engine_digest as current_engine_digest
    from arena.replay import verify
    try:
        guard_checks = (
            check_snapshot_guards()
            + check_runtime_unpack_guard()
            + check_runtime_transcript_preflight()
        )
    except Exception as error:
        print(f"snapshot custody guards: FAIL ({error.__class__.__name__}: {error})")
        return 1
    print(f"snapshot custody guards: PASS ({guard_checks} adversarial checks)")
    preserved = source_sets(collect())

    transcripts = sorted(
        p for p in glob.glob(os.path.join(ROOT, "matches", "**", "*.jsonl"), recursive=True)
        if not p.endswith(".diagnostics.jsonl")
    )
    if not transcripts:
        print("no transcripts to check against")
        return 1

    bad = 0
    for t in transcripts:
        proc = subprocess.run(
            [sys.executable, OUT, t, "--json"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            solo_report = json.loads(proc.stdout.decode("utf-8", "replace"))
            solo = solo_report["replay_verdict"]
        except Exception:
            solo_report = {}
            solo = f"CRASH({proc.stderr.decode('utf-8', 'replace')[:120]})"
        try:
            with open(t, "r", encoding="utf-8") as fh:
                recorded_digest = json.loads(fh.readline())["body"]["engine"]["digest"]
        except Exception:
            recorded_digest = None
        if recorded_digest == current_engine_digest():
            expected = verify(t)["verdict"]
        elif recorded_digest in preserved:
            expected = verdict_with_sources(preserved[recorded_digest], t)
        else:
            expected = verify(t)["verdict"]
        expected_exit = 0 if (
            expected == "PASS"
            and solo_report.get("engine_digest_match") is True
            and solo_report.get("verifier_snapshot_match") is True
        ) else 1
        agree = expected == solo and proc.returncode == expected_exit
        if not agree:
            bad += 1
            print(
                f"  MISMATCH {os.path.basename(t)}: expected={expected}/exit{expected_exit} "
                f"single-file={solo}/exit{proc.returncode}"
            )

    print(f"\nconformance: {len(transcripts) - bad}/{len(transcripts)} transcripts agree "
          f"(package verifier vs single-file verifier)")
    if bad:
        print("FAIL - the single file does not reproduce the referee's verdicts")
    return 1 if bad else 0


if __name__ == "__main__":
    import json  # noqa: E402  (used by check())

    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify conformance against the package")
    ap.add_argument("--snapshot-current", action="store_true",
                    help="preserve the current referee bytes under their engine digest")
    ap.add_argument("--base", default=DEFAULT_BASE, help="where verify.py fetches matches from")
    a = ap.parse_args()

    sys.path.insert(0, ROOT)
    if a.snapshot_current:
        snapshot_current()
    files, dig, versions = build(a.base)
    size = os.path.getsize(OUT)
    print(f"wrote {os.path.relpath(OUT, ROOT)}  —  {len(files)} engine files, "
          f"{versions} engine version(s), {size / 1024:.0f} KB, "
          f"current digest {dig[:16]}...")
    sys.exit(check() if a.check else 0)
