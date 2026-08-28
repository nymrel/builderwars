"""Hash-chained match transcript.

The transcript is the match. A result is not a claim the engine makes; it is the
head of a chain that anyone can recompute from the file. Records are append-only
JSON Lines, each committing to the one before it.

Only the engine process ever holds a writer. Entrants never learn the path.
"""

import copy
import json
import os

from .canonical import GENESIS, canonical_bytes, chain


class ChainBroken(Exception):
    pass


class _DuplicateKey(ValueError):
    pass


def _object_without_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise _DuplicateKey(f"duplicate object key {key!r}")
        obj[key] = value
    return obj


class TranscriptWriter:
    def __init__(self, path):
        self.path = str(path)
        self.prev = GENESIS
        self.seq = 0
        self._records = []
        parent = os.path.dirname(self.path) or "."
        os.makedirs(parent, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags, 0o600)
        try:
            self._fh = open(fd, "w", encoding="utf-8", newline="\n")
        except BaseException:
            os.close(fd)
            raise

    def append(self, kind: str, body: dict) -> dict:
        record = {"kind": kind, "seq": self.seq, "body": body}
        h = chain(self.prev, record)
        line = dict(record)
        line["prev"] = self.prev
        line["hash"] = h
        self._fh.write(
            json.dumps(line, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        )
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._records.append(copy.deepcopy(line))
        self.prev = h
        self.seq += 1
        return copy.deepcopy(line)

    @property
    def records(self):
        """Return a detached snapshot of the exact records appended so far."""
        return copy.deepcopy(self._records)

    @property
    def head(self) -> str:
        return self.prev

    def close(self):
        if not self._fh.closed:
            self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def load(path):
    records = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line, object_pairs_hook=_object_without_duplicate_keys)
            except _DuplicateKey as e:
                raise ChainBroken(f"line {lineno}: duplicate object key") from e
            except (ValueError, RecursionError) as e:
                raise ChainBroken(f"line {lineno}: not valid JSON ({e.__class__.__name__})") from e
            if not isinstance(parsed, dict):
                raise ChainBroken(f"line {lineno}: record must be a JSON object")
            records.append(parsed)
    return records


_RECORD_KEYS = frozenset({"kind", "seq", "body", "prev", "hash"})
_HEX_DIGITS = frozenset("0123456789abcdef")


def _hex64(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX_DIGITS


def verify_chain(records):
    """Recompute every hash. Returns (ok, error_or_None).

    This is the check that makes post-hoc editing detectable: change one byte of
    one body and every subsequent hash stops matching. Every record is hostile
    input: shape, types, exact key set, and encodability are enforced here so no
    crafted file can crash a caller.
    """
    if not isinstance(records, list):
        return False, "records must be a list"
    prev = GENESIS
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            return False, f"record {i}: record must be a JSON object"
        keys = set(rec)
        if keys != _RECORD_KEYS:
            missing = sorted(_RECORD_KEYS - keys)
            extra = sorted(keys - _RECORD_KEYS)
            return False, (
                f"record {i}: record must hold exactly kind,seq,body,prev,hash "
                f"(missing={missing}, unexpected={extra})"
            )
        if not isinstance(rec["kind"], str) or not rec["kind"]:
            return False, f"record {i}: kind must be a non-empty string"
        if not isinstance(rec["seq"], int) or isinstance(rec["seq"], bool):
            return False, f"record {i}: seq must be an integer"
        if not isinstance(rec["body"], dict):
            return False, f"record {i}: body must be a JSON object"
        if not _hex64(rec["prev"]) or not _hex64(rec["hash"]):
            return False, f"record {i}: prev and hash must be 64-char lowercase hex"
        if rec["seq"] != i:
            return False, f"record {i}: seq is {rec['seq']}, expected {i}"
        if rec["prev"] != prev:
            return False, f"record {i}: prev does not match previous record's hash"
        body = {"kind": rec["kind"], "seq": rec["seq"], "body": rec["body"]}
        try:
            expect = chain(prev, body)
        except Exception as e:  # non-canonical content smuggled into a record
            return False, f"record {i}: body is not canonically encodable ({e.__class__.__name__})"
        if expect != rec["hash"]:
            return False, f"record {i}: hash mismatch (record was altered)"
        prev = rec["hash"]
    return True, None


def head_of(records):
    return records[-1]["hash"] if records and isinstance(records[-1], dict) else GENESIS


def find(records, kind):
    return [r for r in records if isinstance(r, dict) and r.get("kind") == kind]


def first(records, kind):
    for r in records:
        if isinstance(r, dict) and r.get("kind") == kind:
            return r
    return None


__all__ = [
    "TranscriptWriter",
    "ChainBroken",
    "load",
    "verify_chain",
    "head_of",
    "find",
    "first",
    "canonical_bytes",
]
