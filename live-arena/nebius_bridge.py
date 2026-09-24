"""Hackathon-only Nebius/NVIDIA move bridge.

Uses the existing BuilderWars local HTTP/auth boundary while routing model calls
to an NVIDIA open model on Nebius Token Factory. This is not admission to the
general BuilderWars provider catalog.
"""
from __future__ import annotations

import argparse
import secrets
from urllib.parse import urlparse

from bridge import BridgeServer, handler_for

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from entrants.nebius_backend import NebiusTokenFactoryBackend


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True, help="Exact BuilderWars website origin")
    parser.add_argument(
        "--model",
        default=NebiusTokenFactoryBackend.DEFAULT_MODEL,
        help="Exact NVIDIA model id in the current Nebius Token Factory catalog",
    )
    parser.add_argument(
        "--allow-model-requests",
        action="store_true",
        required=True,
        help="Authorize requests billed to your own Nebius Token Factory project",
    )
    parser.add_argument("--max-calls", type=int, default=40)
    parser.add_argument("--timeout-s", type=int, default=110)
    args = parser.parse_args()

    url = urlparse(args.origin)
    if (
        url.scheme not in ("http", "https")
        or url.path
        or url.query
        or url.fragment
        or url.username
        or not url.hostname
        or (url.scheme == "http" and url.hostname not in ("localhost", "127.0.0.1"))
    ):
        parser.error(
            "Use an exact HTTPS origin or a loopback development origin, "
            "without a trailing slash."
        )
    if not 1 <= args.max_calls <= 200:
        parser.error("Choose --max-calls between 1 and 200.")
    if not 1 <= args.timeout_s <= 3600:
        parser.error("Choose --timeout-s between 1 and 3600.")

    backend = NebiusTokenFactoryBackend(
        model=args.model,
        timeout_s=args.timeout_s,
    )
    token = secrets.token_urlsafe(32)
    server = BridgeServer(
        ("127.0.0.1", 8765),
        handler_for(
            backend,
            token,
            args.origin,
            backend.label,
            args.max_calls,
        ),
    )

    print(
        "BuilderWars Nebius hackathon bridge: "
        "http://127.0.0.1:8765/move\n"
        f"Allowed site: {args.origin}\n"
        f"Provider: {backend.label}\n"
        f"Request limit: {args.max_calls}"
    )
    print(f"Paste this temporary local token into your site's harness connection: {token}")
    print(
        "Keep this terminal open. Ctrl+C disconnects. "
        "NEBIUS_API_KEY remains in this local process environment."
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
