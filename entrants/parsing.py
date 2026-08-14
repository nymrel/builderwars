"""Move parsing, shared verbatim by both reference harnesses.

Deliberately identical for both arms. Parsing quality is real harness work, but
if the two reference entrants parsed differently the series would be measuring
my regex rather than the thing it claims to measure. One parser, both arms, so
the only variable left is what each harness does with what it parsed.

Handles the shapes a model actually produces, which is a wider set than the one
I first assumed. Probed 2026-08-14: `qwen2.5:7b` answers a nim prompt with a
bare JSON object. The original prose-only regex silently discarded a perfectly
legal move and the harness forfeited — a defect in the harness, invisible until
a real model replaced the stub.
"""

import json
import re

_PROSE = (
    re.compile(r"take\s+(?P<take>\d+)\s+(?:objects?\s+)?from\s+heap\s+(?P<heap>\d+)", re.I),
    re.compile(r"heap\s+(?P<heap>\d+)\s*[,:]?\s*take\s+(?P<take>\d+)", re.I),
    re.compile(r"remove\s+(?P<take>\d+)\s+from\s+(?:heap\s+)?(?P<heap>\d+)", re.I),
)

_JSON_OBJ = re.compile(r"\{[^{}]*\}")


def parse_move(text):
    """Pull a {"heap", "take"} move out of arbitrary model output, or None."""
    if not text:
        return None

    # JSON first: an explicit object is less ambiguous than prose that happens
    # to contain digits.
    for candidate in _JSON_OBJ.findall(text):
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        heap, take = obj.get("heap"), obj.get("take")
        if isinstance(heap, bool) or isinstance(take, bool):
            continue
        if isinstance(heap, int) and isinstance(take, int):
            return {"heap": heap, "take": take}

    for pattern in _PROSE:
        m = pattern.search(text)
        if m:
            return {"heap": int(m.group("heap")), "take": int(m.group("take"))}

    return None
