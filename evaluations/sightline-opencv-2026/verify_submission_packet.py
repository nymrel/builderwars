"""Fail-closed verifier for the draft judge-facing Sightline packet."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


PACKET_ROOT = Path(__file__).with_name("submission-packet")
ALLOWED_FILES = (
    "ARCHITECTURE.draft.md",
    "DEMO_SCRIPT.draft.md",
    "LIMITATIONS.draft.md",
    "TECHNICAL_REPORT.draft.md",
)
MAX_FILE_BYTES = 32768
FORBIDDEN = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?:^|\s)/Users/"),
    re.compile(r"[A-Za-z]:\\Users\\"),
    re.compile(r"(?i)(?:api[_-]?key|secret|access[_-]?token)\s*[:=]\s*[^\s`]{8,}"),
)
REQUIRED_MARKER = "Draft, Not Submitted"


def verify_packet(root: Path = PACKET_ROOT) -> dict[str, Any]:
    if not root.is_dir():
        raise ValueError("submission packet directory is missing")
    observed = tuple(sorted(path.name for path in root.iterdir() if path.is_file()))
    if observed != ALLOWED_FILES:
        raise ValueError("submission packet allowlist mismatch")

    receipts = []
    for name in ALLOWED_FILES:
        path = root / name
        payload = path.read_bytes()
        if not payload or len(payload) > MAX_FILE_BYTES:
            raise ValueError(f"{name}: size outside 1..{MAX_FILE_BYTES}")
        text = payload.decode("utf-8")
        if REQUIRED_MARKER not in text:
            raise ValueError(f"{name}: draft marker missing")
        for pattern in FORBIDDEN:
            if pattern.search(text):
                raise ValueError(f"{name}: forbidden sensitive pattern")
        receipts.append(
            {
                "path": name,
                "bytes": len(payload),
                "sha256": sha256(payload).hexdigest(),
            }
        )

    return {
        "schema": "sightline.submission-packet-receipt.v1",
        "status": "draft_not_submitted",
        "files": receipts,
        "secret_pattern_matches": 0,
        "local_path_matches": 0,
        "publication_authorized": False,
        "submission_authorized": False,
    }


def main() -> int:
    print(json.dumps(verify_packet(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
