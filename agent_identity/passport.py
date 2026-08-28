"""Compatibility surface for the engine-bound Agent Passport implementation.

All schema, canonicalization, signing, and verification logic lives in
``arena.passport`` so it is covered by the referee engine digest and embedded in
the standalone verifier. This module intentionally contains no logic.
"""

from arena.passport import *  # noqa: F401,F403
from arena.passport import __all__
