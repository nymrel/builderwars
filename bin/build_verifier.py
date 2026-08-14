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
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARENA = os.path.join(ROOT, "arena")
OUT = os.path.join(ROOT, "verify.py")

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


HEADER = '''#!/usr/bin/env python3
"""BuilderWars — verify one match, from nothing.

    python verify.py <match-id>        fetches the match and checks it
    python verify.py path/to.jsonl     checks a transcript you already have
    python verify.py <match-id> --json full report as JSON

Exit code 0 means PASS. Stock Python 3. No dependencies, no account, no key.

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

# relpath -> base64 of the file's raw bytes, exactly as the referee hashed them.
SOURCES = {{
{sources}
}}

ENGINE_DIGEST = "{engine_digest}"


def _unpack():
    root = tempfile.mkdtemp(prefix="builderwars-verify-")
    atexit.register(shutil.rmtree, root, True)
    pkg = os.path.join(root, "arena")
    for rel, b64 in SOURCES.items():
        dest = os.path.join(pkg, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:          # binary: hashes are over raw bytes
            fh.write(base64.b64decode(b64))
    sys.path.insert(0, root)
    return root


def _fetch(arg):
    """A local path is used as-is. Anything else is treated as a match id or URL."""
    if os.path.exists(arg):
        return arg, False
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
    return tmp.name, True


def main():
    ap = argparse.ArgumentParser(description="Verify one BuilderWars match.")
    ap.add_argument("match", help="match id, URL, or path to a transcript")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    _unpack()
    from arena.replay import verify          # the referee's own verifier

    path, fetched = _fetch(args.match)
    report = verify(path)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report["verdict"] == "PASS" else 1

    print(f"match      : {{report.get('match_id')}}  game={{report.get('game')}} seed={{report.get('seed')}}")
    if fetched:
        print(f"source     : {{BASE}}/m/{{args.match}}.jsonl")
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
    print(f"VERDICT: {{report['verdict']}}")
    if report["verdict"] == "PASS":
        print("\\nthis proves:")
        for p in report["proves"]:
            print(f"  + {{p}}")
        print("\\nthis does NOT prove:")
        for p in report["does_not_prove"]:
            print(f"  - {{p}}")
    else:
        for e in report["errors"]:
            print(f"  ! {{e}}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
'''


def build(base_url):
    files = collect()
    lines = []
    for rel, raw in files:
        b64 = base64.b64encode(raw).decode("ascii")
        chunks = [b64[i:i + 88] for i in range(0, len(b64), 88)] or [""]
        body = "\n".join(f'        "{c}"' for c in chunks)
        lines.append(f'    "{rel}":\n{body},')

    # Same computation integrity.engine_digest performs, so we can print it and
    # let the transcript check catch any drift.
    from arena.canonical import digest  # noqa: E402
    pairs = [[rel, hashlib.sha256(raw).hexdigest()] for rel, raw in files]

    src = HEADER.format(
        base=base_url,
        sources="\n".join(lines),
        engine_digest=digest(pairs),
    )
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src)
    return files, digest(pairs)


def check():
    """Conformance: the single file must agree with the package on every transcript.

    A verifier that disagrees with the referee is worse than no verifier, so this
    compares verdicts one by one rather than trusting that embedding "obviously"
    preserves behaviour.
    """
    sys.path.insert(0, ROOT)
    from arena.replay import verify

    transcripts = sorted(
        p for p in glob.glob(os.path.join(ROOT, "matches", "**", "*.jsonl"), recursive=True)
        if not p.endswith(".diagnostics.jsonl")
    )
    if not transcripts:
        print("no transcripts to check against")
        return 1

    bad = 0
    for t in transcripts:
        pkg = verify(t)["verdict"]
        proc = subprocess.run(
            [sys.executable, OUT, t, "--json"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            solo = json.loads(proc.stdout.decode("utf-8", "replace"))["verdict"]
        except Exception:
            solo = f"CRASH({proc.stderr.decode('utf-8', 'replace')[:120]})"
        agree = pkg == solo
        if not agree:
            bad += 1
            print(f"  MISMATCH {os.path.basename(t)}: package={pkg} single-file={solo}")

    print(f"\nconformance: {len(transcripts) - bad}/{len(transcripts)} transcripts agree "
          f"(package verifier vs single-file verifier)")
    if bad:
        print("FAIL - the single file does not reproduce the referee's verdicts")
    return 1 if bad else 0


if __name__ == "__main__":
    import json  # noqa: E402  (used by check())

    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify conformance against the package")
    ap.add_argument("--base", default=DEFAULT_BASE, help="where verify.py fetches matches from")
    a = ap.parse_args()

    sys.path.insert(0, ROOT)
    files, dig = build(a.base)
    size = os.path.getsize(OUT)
    print(f"wrote {os.path.relpath(OUT, ROOT)}  —  {len(files)} engine files, "
          f"{size / 1024:.0f} KB, engine digest {dig[:16]}...")
    sys.exit(check() if a.check else 0)
