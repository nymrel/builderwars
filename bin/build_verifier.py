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
import glob
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARENA = os.path.join(ROOT, "arena")
OUT = os.path.join(ROOT, "verify.py")
SNAPSHOT_DIR = os.path.join(ROOT, "bin", "verifier_snapshots")

DEFAULT_BASE = "https://nymrel.com/builderwars"


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
        with open(path, "r", encoding="utf-8") as fh:
            if json.load(fh) != payload:
                raise SystemExit(f"snapshot collision for {engine_digest}")
        print(f"snapshot already current: {os.path.relpath(path, ROOT)}")
        return path
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, sort_keys=True, separators=(",", ":"))
        fh.write("\n")
    print(f"snapshotted {len(files)} files -> {os.path.relpath(path, ROOT)}")
    return path


def source_sets(current_files):
    """Return every preserved engine plus the current one, keyed by digest."""
    sets = {}
    if os.path.isdir(SNAPSHOT_DIR):
        for path in sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json"))):
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            engine_digest = payload.get("engineDigest")
            sources = payload.get("sources")
            if not isinstance(engine_digest, str) or not isinstance(sources, dict):
                raise SystemExit(f"invalid verifier snapshot: {path}")
            if engine_digest in sets and sets[engine_digest] != sources:
                raise SystemExit(f"duplicate verifier digest with different bytes: {engine_digest}")
            sets[engine_digest] = sources
    sets[digest_for(current_files)] = encode_sources(current_files)
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
import json
import os
import shutil
import sys
import tempfile
import urllib.request

BASE = os.environ.get("BUILDERWARS_BASE", "{base}")

# engine digest -> (relpath -> base64 bytes). Historical referee builds remain
# embedded so a new game cannot strand already-published match receipts.
SOURCE_SETS = {source_sets}
DEFAULT_ENGINE_DIGEST = "{engine_digest}"


def _unpack(sources):
    root = tempfile.mkdtemp(prefix="builderwars-verify-")
    atexit.register(shutil.rmtree, root, True)
    pkg = os.path.join(root, "arena")
    for rel, b64 in sources.items():
        dest = os.path.join(pkg, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:          # binary: hashes are over raw bytes
            fh.write(base64.b64decode(b64))
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


def _inspect_transcript(path):
    """Return (engine digest, signed-block-present, preflight error).

    This wrapper-level scan applies even when an old embedded snapshot predates
    duplicate-key and passport handling. A signed block can never be silently
    interpreted by a legacy-only snapshot.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            records = [
                json.loads(line, object_pairs_hook=_object_without_duplicate_keys)
                for line in fh
                if line.strip()
            ]
        header = next((row for row in records if row.get("kind") == "header"), None)
        if not isinstance(header, dict):
            return None, False, "transcript preflight: no header record"
        body = header.get("body", {{}})
        entrants = body.get("entrants")
        signed = isinstance(entrants, list) and any(
            isinstance(row, dict) and "agent_passport" in row for row in entrants
        )
        return body.get("engine", {{}}).get("digest"), signed, None
    except Exception as error:
        return None, False, f"transcript preflight: {{error.__class__.__name__}}: {{error}}"


def _fetch(arg):
    """A local path is used as-is. Anything else is treated as a match id or URL."""
    if os.path.exists(arg):
        return arg, None
    url = arg if arg.startswith(("http://", "https://")) else f"{{BASE}}/m/{{arg}}.jsonl"
    tmp = tempfile.NamedTemporaryFile(prefix="builderwars-", suffix=".jsonl", delete=False)
    atexit.register(os.unlink, tmp.name)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            tmp.write(resp.read())
    except Exception as e:
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
    selected_digest = recorded_digest if recorded_digest in SOURCE_SETS else DEFAULT_ENGINE_DIGEST
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
    files = collect()
    engine_digest = digest_for(files)
    sets = source_sets(files)

    src = HEADER.format(
        base=base_url,
        source_sets=render_source_sets(sets),
        engine_digest=engine_digest,
    )
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src)
    return files, engine_digest, len(sets)


def verdict_with_sources(sources, transcript):
    """Run one preserved referee in a fresh interpreter and return its verdict."""
    with tempfile.TemporaryDirectory(prefix="builderwars-check-") as root:
        package = os.path.join(root, "arena")
        for rel, b64 in sources.items():
            path = os.path.join(package, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(base64.b64decode(b64))
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


def check():
    """Conformance: the single file must agree with the package on every transcript.

    A verifier that disagrees with the referee is worse than no verifier, so this
    compares verdicts one by one rather than trusting that embedding "obviously"
    preserves behaviour.
    """
    sys.path.insert(0, ROOT)
    from arena.integrity import engine_digest as current_engine_digest
    from arena.replay import verify
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
