"""Hash-chained match transcript.

The transcript is the match. A result is not a claim the engine makes; it is the
head of a chain that anyone can recompute from the file. Records are append-only
JSON Lines, each committing to the one before it.

Only the engine process ever holds a writer. Entrants never learn the path.
"""

import json
import os

from .canonical import GENESIS, canonical_bytes, chain


class ChainBroken(Exception):
    pass


class TranscriptWriter:
    def __init__(self, path):
        self.path = str(path)
        self.prev = GENESIS
        self.seq = 0
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._fh = open(self.path, "w", encoding="utf-8", newline="\n")

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
        self.prev = h
        self.seq += 1
        return line

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
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ChainBroken(f"line {lineno}: not valid JSON ({e})") from e
    return records


def verify_chain(records):
    """Recompute every hash. Returns (ok, error_or_None).

    This is the check that makes post-hoc editing detectable: change one byte of
    one body and every subsequent hash stops matching.
    """
    prev = GENESIS
    for i, rec in enumerate(records):
        for field in ("kind", "seq", "body", "prev", "hash"):
            if field not in rec:
                return False, f"record {i}: missing field {field!r}"
        if rec["seq"] != i:
            return False, f"record {i}: seq is {rec['seq']}, expected {i}"
        if rec["prev"] != prev:
            return False, f"record {i}: prev does not match previous record's hash"
        body = {"kind": rec["kind"], "seq": rec["seq"], "body": rec["body"]}
        try:
            expect = chain(prev, body)
        except Exception as e:  # non-canonical content smuggled into a record
            return False, f"record {i}: body is not canonically encodable ({e})"
        if expect != rec["hash"]:
            return False, f"record {i}: hash mismatch (record was altered)"
        prev = rec["hash"]
    return True, None


def head_of(records):
    return records[-1]["hash"] if records else GENESIS


def find(records, kind):
    return [r for r in records if r["kind"] == kind]


def first(records, kind):
    for r in records:
        if r["kind"] == kind:
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
