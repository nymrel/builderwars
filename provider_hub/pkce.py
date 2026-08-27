"""OpenRouter OAuth PKCE — current official contract, S256 only.

Source of truth: https://openrouter.ai/docs/guides/overview/auth/oauth

The flow a customer runner performs:

1. Generate an RFC 7636 verifier + S256 challenge.
2. Open the authorization URL built from EXACTLY three query parameters:
   ``callback_url``, ``code_challenge``, ``code_challenge_method=S256``.
   OpenRouter does not take ``client_id``, ``redirect_uri``,
   ``response_type``, ``scope``, or an echoed ``state`` parameter — none of
   those are ever invented here.
3. The provider redirects to the caller's own callback URL with a one-time
   ``code``. Callback parsing is bound to the exact expected callback base
   URL: scheme, host, effective port, and path must match exactly. When callers
   control the route, ``new_callback_path()`` supplies a fresh 128-bit path
   segment for additional correlation without inventing a provider-echoed
   ``state`` field.
4. Exchange the code for the customer's key with a POST body of EXACTLY
   ``code``, ``code_verifier``, and ``code_challenge_method: "S256"``.

Hard rules enforced here:

* HTTPS callbacks anywhere, loopback HTTP callbacks only with an explicit port;
* plain challenge mode does not exist here — anything other than S256 rejects;
* authorization/exchange endpoints pinned to an allowlisted HTTPS origin;
* redirects are refused so the one-time code can never be forwarded off-origin;
* the verifier, the callback code, and the exchanged key live only inside
  ``SecretValue`` wrappers whose ``repr``/``str`` never reveal them;
* response sizes are capped and error messages sanitized;
* network transport is injectable — the whole suite runs offline and no live
  exchange is ever performed by this repository.
"""

import base64
import hashlib
import http.server
import json
import re
import secrets as _secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from provider_hub.secrets import SecretValue

AUTHORIZE_ENDPOINT = "https://openrouter.ai/auth"
EXCHANGE_ENDPOINT = "https://openrouter.ai/api/v1/auth/keys"
_PINNED_AUTHORIZE_ENDPOINT = "https://openrouter.ai/auth"
_PINNED_EXCHANGE_ENDPOINT = "https://openrouter.ai/api/v1/auth/keys"
ALLOWED_ORIGINS = ("openrouter.ai",)

VERIFIER_LENGTH = 64
_UNRESERVED_RE = re.compile(r"^[A-Za-z0-9\-._~]+$")
_CHALLENGE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
# Length/control-character safety only: OpenRouter does not document the
# authorization-code alphabet, so nothing tighter than printable ASCII without
# whitespace or control characters is asserted.
_CODE_RE = re.compile(r"^[\x21-\x7e]{8,2048}$")
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
_EXCHANGE_TIMEOUT_S = 30
_MAX_RESPONSE_BYTES = 65536
_MAX_CALLBACK_TARGET_BYTES = 8192
_MIN_LOOPBACK_WAIT_S = 10
_MAX_LOOPBACK_WAIT_S = 600


class PkceError(ValueError):
    """Any PKCE primitive failure. Messages never carry secret values."""


# ---------------------------------------------------------------------------
# verifier / challenge
# ---------------------------------------------------------------------------


def new_verifier():
    """Fresh RFC 7636 verifier from the unreserved set, wrapped as a secret."""
    alphabet = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    )
    value = "".join(_secrets.choice(alphabet) for _ in range(VERIFIER_LENGTH))
    return SecretValue(value)


def new_callback_path():
    """Return a callback path with a fresh 128-bit correlation segment."""
    return "/buildwars/callback/" + _secrets.token_urlsafe(16)


def _verifier_text(verifier_secret):
    if not isinstance(verifier_secret, SecretValue):
        raise PkceError("verifier must be a SecretValue")
    value = verifier_secret.reveal()
    if (
        not isinstance(value, str)
        or not 43 <= len(value) <= 128
        or not _UNRESERVED_RE.fullmatch(value)
    ):
        raise PkceError("verifier must be 43-128 unreserved characters")
    return value


def challenge_from_verifier(verifier_secret):
    """BASE64URL(SHA256(verifier)) with padding stripped — the S256 challenge."""
    digest = hashlib.sha256(_verifier_text(verifier_secret).encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def assert_plain_challenge_rejected(method):
    """Explicit guard used by tooling: any method other than S256 fails."""
    if method != "S256":
        raise PkceError(f"challenge method {method!r} rejected; only S256 is permitted")
    return True


# ---------------------------------------------------------------------------
# redirect / callback validation
# ---------------------------------------------------------------------------


def validate_redirect_uri(uri):
    """Permit HTTPS anywhere; HTTP only on loopback hosts with explicit port."""
    if not isinstance(uri, str) or not 1 <= len(uri) <= 4096:
        raise PkceError("redirect uri must be a string")
    try:
        parsed = urllib.parse.urlsplit(uri)
    except ValueError as error:
        raise PkceError(f"unparseable redirect uri: {error.__class__.__name__}") from None
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    try:
        port = parsed.port
    except ValueError:
        raise PkceError("callback uri has an invalid port") from None
    if scheme == "https":
        if not host:
            raise PkceError("https callback needs a host")
    elif scheme == "http":
        if port is None:
            raise PkceError("loopback http callback requires an explicit port")
        if host is None or host.lower() not in _LOOPBACK_HOSTS:
            raise PkceError("http callbacks are only allowed on loopback hosts")
    else:
        raise PkceError(f"unsupported callback scheme {scheme!r}")
    if parsed.username or parsed.password:
        raise PkceError("callback uri must not embed userinfo")
    if parsed.fragment:
        raise PkceError("callback uri must not carry a fragment")
    return uri


def _effective_port(parsed):
    try:
        port = parsed.port
    except ValueError:
        raise PkceError("callback uri has an invalid port") from None
    if port is not None:
        return port
    if parsed.scheme.lower() == "https":
        return 443
    if parsed.scheme.lower() == "http":
        return 80
    raise PkceError(f"unsupported callback scheme {parsed.scheme!r}")


def _assert_allowed_origin(url, what):
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        raise PkceError(f"{what} endpoint is not a valid URL") from None
    if parsed.scheme != "https":
        raise PkceError(f"{what} endpoint must be https")
    if parsed.username or parsed.password:
        raise PkceError(f"{what} endpoint must not embed userinfo")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_ORIGINS:
        raise PkceError(f"{what} endpoint origin {host!r} is not allowlisted")
    try:
        port = parsed.port
    except ValueError:
        raise PkceError(f"{what} endpoint port is invalid") from None
    if port not in (None, 443):
        raise PkceError(f"{what} endpoint must use the default HTTPS port")


def _assert_pinned_endpoint(url, expected, what):
    _assert_allowed_origin(url, what)
    if url != expected:
        raise PkceError(f"{what} endpoint does not match the pinned URL")


def parse_callback(callback_uri, *, expected_callback):
    """Validate an OAuth redirect against the EXACT expected callback URL.

    Binding is exact on scheme, host, effective port (default ports fold to
    their scheme default), and path — so a caller may use an unguessable
    callback path as its correlation token instead of a state round-trip.
    The query must contain exactly one parameter, named ``code``. Returns the
    wrapped one-time code.
    """
    validate_redirect_uri(callback_uri)
    validate_redirect_uri(expected_callback)
    try:
        actual = urllib.parse.urlsplit(callback_uri)
        expected = urllib.parse.urlsplit(expected_callback)
    except ValueError:
        raise PkceError("unparseable callback uri") from None
    if expected.query:
        raise PkceError("expected callback must not contain a query")
    if actual.scheme.lower() != expected.scheme.lower():
        raise PkceError("callback scheme does not match the expected callback")
    actual_host = (actual.hostname or "").lower()
    expected_host = (expected.hostname or "").lower()
    if actual_host != expected_host:
        raise PkceError("callback host does not match the expected callback")
    if _effective_port(actual) != _effective_port(expected):
        raise PkceError("callback port does not match the expected callback")
    if actual.path != expected.path:
        raise PkceError("callback path does not match the expected callback")

    try:
        pairs = urllib.parse.parse_qsl(
            actual.query, keep_blank_values=True, max_num_fields=4
        )
    except ValueError:
        raise PkceError("callback query has too many fields") from None
    seen_keys = set()
    for key, _value in pairs:
        if key in seen_keys:
            raise PkceError(f"duplicate callback parameter {key!r}")
        seen_keys.add(key)
    codes = [value for key, value in pairs if key == "code"]
    if len(pairs) != 1 or len(codes) != 1:
        raise PkceError(
            f"callback query must contain exactly one 'code' parameter, got "
            f"{sorted(seen_keys)}"
        )
    code = codes[0]
    if not isinstance(code, str) or not _CODE_RE.fullmatch(code):
        raise PkceError("callback code is malformed")
    return SecretValue(code)


# ---------------------------------------------------------------------------
# authorization URL — exactly the official parameters
# ---------------------------------------------------------------------------

_OFFICIAL_AUTHORIZE_PARAMS = frozenset(
    {"callback_url", "code_challenge", "code_challenge_method"}
)


def build_authorize_url(*, callback_url, code_challenge):
    """Construct the PKCE authorization URL per the current OpenRouter docs.

    Exactly three query parameters: ``callback_url``, ``code_challenge``,
    ``code_challenge_method=S256``. Generic OAuth parameters such as
    ``client_id``, ``redirect_uri``, ``response_type``, ``scope``, or a
    provider-echoed ``state`` are deliberately never sent.
    """
    validate_redirect_uri(callback_url)
    if urllib.parse.urlsplit(callback_url).query:
        raise PkceError("callback_url must not contain a query; use an unguessable path")
    if not isinstance(code_challenge, str) or not _CHALLENGE_RE.fullmatch(code_challenge):
        raise PkceError("challenge must be the 43-char S256 base64url encoding")
    _assert_pinned_endpoint(
        AUTHORIZE_ENDPOINT, _PINNED_AUTHORIZE_ENDPOINT, "authorization"
    )
    params = {
        "callback_url": callback_url,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if set(params) != _OFFICIAL_AUTHORIZE_PARAMS:
        raise PkceError("authorization parameters drifted from the official contract")
    return AUTHORIZE_ENDPOINT + "?" + urllib.parse.urlencode(params)


# ---------------------------------------------------------------------------
# exchange
# ---------------------------------------------------------------------------


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect so the POSTed code cannot leave the origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def _code_text(code_secret):
    if not isinstance(code_secret, SecretValue):
        raise PkceError("exchange code must be a SecretValue")
    value = code_secret.reveal()
    if not isinstance(value, str) or not _CODE_RE.fullmatch(value):
        raise PkceError("exchange code is malformed")
    return value


def build_exchange_request(code_secret, verifier_secret):
    """POST body + headers for the key exchange. Never logs either secret."""
    code_text = _code_text(code_secret)
    verifier_text = _verifier_text(verifier_secret)
    _assert_pinned_endpoint(
        EXCHANGE_ENDPOINT, _PINNED_EXCHANGE_ENDPOINT, "exchange"
    )
    body = json.dumps(
        {
            "code": code_text,
            "code_verifier": verifier_text,
            "code_challenge_method": "S256",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        EXCHANGE_ENDPOINT,
        data=body,
        headers={
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    return request


def default_transport(request):
    """Real network transport. Production path only; tests inject fakes."""
    try:
        with _OPENER.open(request, timeout=_EXCHANGE_TIMEOUT_S) as response:
            return response.getcode(), response.read(_MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        try:
            error.read()
        except Exception:
            pass
        raise PkceError(f"exchange failed with HTTP {error.code}") from None


def parse_exchange_response(raw_bytes):
    """Parse the documented key response while keeping the key wrapped.

    OpenRouter currently returns ``key`` and may also return ``user_id`` as a
    string or null. No other response fields are accepted.
    """
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise PkceError("exchange response must be bytes")
    raw_bytes = bytes(raw_bytes)
    if len(raw_bytes) > _MAX_RESPONSE_BYTES:
        raise PkceError("exchange response exceeds size cap")
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PkceError(
            f"exchange response is not JSON ({error.__class__.__name__})"
        ) from None
    keys = set(payload) if isinstance(payload, dict) else set()
    if keys not in ({"key"}, {"key", "user_id"}):
        raise PkceError(
            f"exchange response must have 'key' and optional 'user_id', got "
            f"{sorted(payload) if isinstance(payload, dict) else type(payload).__name__}"
        )
    if "user_id" in payload:
        user_id = payload["user_id"]
        if user_id is not None and (
            not isinstance(user_id, str)
            or not 1 <= len(user_id) <= 256
            or any(ord(ch) < 33 or ord(ch) > 126 for ch in user_id)
        ):
            raise PkceError("exchange response user_id has unexpected shape")
    key = payload["key"]
    if (
        not isinstance(key, str)
        or not key.startswith("sk-or-v1-")
        or not 24 <= len(key) <= 1024
        or any(ord(ch) < 33 or ord(ch) > 126 for ch in key)
    ):
        raise PkceError("exchanged key has unexpected shape")
    return SecretValue(key)


def exchange(code_secret, verifier_secret, *, transport=default_transport):
    """Exchange the wrapped code AND wrapped verifier for the customer's key.

    Both secrets are required to be ``SecretValue`` wrappers. Errors are
    sanitized to status/class names so neither secret can leak into exception
    text or logs. Redirects are refused before any follow-up request could
    forward the authorization material off-origin.
    """
    request = build_exchange_request(code_secret, verifier_secret)
    try:
        status, raw = transport(request)
    except urllib.error.HTTPError as error:
        try:
            error.read()
        except Exception:
            pass
        raise PkceError(f"exchange failed with HTTP {error.code}") from None
    except PkceError:
        raise
    except Exception as error:
        raise PkceError(
            f"exchange transport failed: {error.__class__.__name__}"
        ) from None
    if status != 200:
        raise PkceError(f"exchange returned HTTP {status}")
    return parse_exchange_response(raw)


# ---------------------------------------------------------------------------
# customer-local loopback orchestration
# ---------------------------------------------------------------------------


class _LoopbackCallbackServer(http.server.HTTPServer):
    """One-thread bounded server whose errors never render callback material."""

    def handle_error(self, _request, _client_address):  # noqa: D102
        return


class _LoopbackCallbackHandler(http.server.BaseHTTPRequestHandler):
    """Receive one exact provider redirect without logging request material."""

    server_version = "AgentWarsLoopback"
    sys_version = ""

    def log_message(self, _format, *_args):  # noqa: D102
        return

    def _reply(self, status, body):
        raw = body.encode("ascii")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=us-ascii")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)
        except OSError:
            return

    def do_GET(self):  # noqa: N802,D102
        if len(self.path.encode("utf-8", errors="ignore")) > _MAX_CALLBACK_TARGET_BYTES:
            self._reply(414, "Request rejected.\n")
            return
        try:
            target = urllib.parse.urlsplit(self.path)
        except ValueError:
            self._reply(400, "Request rejected.\n")
            return
        if target.scheme or target.netloc or target.fragment:
            self._reply(400, "Request rejected.\n")
            return
        if target.path != self.server.callback_path:  # type: ignore[attr-defined]
            self._reply(404, "Not found.\n")
            return
        callback_uri = self.server.callback_url  # type: ignore[attr-defined]
        if target.query:
            callback_uri += "?" + target.query
        try:
            code = parse_callback(
                callback_uri,
                expected_callback=self.server.callback_url,  # type: ignore[attr-defined]
            )
        except PkceError:
            self._reply(400, "Authorization response rejected. Retry from AgentWars.\n")
            return
        self.server.callback_code = code  # type: ignore[attr-defined]
        self._reply(
            200,
            "Authorization received. Return to AgentWars and close this tab.\n",
        )

    def do_HEAD(self):  # noqa: N802,D102
        self._reply(405, "Method not allowed.\n")

    def do_POST(self):  # noqa: N802,D102
        self._reply(405, "Method not allowed.\n")


def authorize_openrouter_loopback(
    *,
    timeout_seconds=180,
    transport=default_transport,
    browser_opener=None,
    announce=None,
):
    """Authorize one customer-owned OpenRouter key for bounded local use.

    The listener binds only to IPv4 loopback on an OS-assigned port. The
    callback path carries a fresh 128-bit correlation segment. Wrong paths and
    malformed callbacks are rejected without ending the bounded wait, so a
    browser favicon request cannot consume the flow. The returned key remains
    wrapped and is never written or printed here. This function controls local
    custody only; it does not claim or attempt provider-side key revocation.
    """

    if type(timeout_seconds) is not int or not (
        _MIN_LOOPBACK_WAIT_S <= timeout_seconds <= _MAX_LOOPBACK_WAIT_S
    ):
        raise PkceError("loopback wait must be an integer from 10 to 600 seconds")
    if browser_opener is None:
        import webbrowser

        browser_opener = webbrowser.open
    if not callable(browser_opener):
        raise PkceError("browser opener must be callable")
    if announce is not None and not callable(announce):
        raise PkceError("authorization announcer must be callable")

    verifier = new_verifier()
    challenge = challenge_from_verifier(verifier)
    callback_path = new_callback_path()
    try:
        server = _LoopbackCallbackServer(
            ("127.0.0.1", 0), _LoopbackCallbackHandler, bind_and_activate=True
        )
    except OSError as error:
        raise PkceError(
            f"loopback callback could not bind: {error.__class__.__name__}"
        ) from None

    try:
        port = server.server_address[1]
        callback_url = f"http://127.0.0.1:{port}{callback_path}"
        authorize_url = build_authorize_url(
            callback_url=callback_url,
            code_challenge=challenge,
        )
        server.callback_path = callback_path
        server.callback_url = callback_url
        server.callback_code = None

        if announce is not None:
            try:
                announce(authorize_url)
            except Exception as error:
                raise PkceError(
                    f"authorization announcement failed: {error.__class__.__name__}"
                ) from None
        try:
            browser_opener(authorize_url)
        except Exception as error:
            raise PkceError(
                f"browser open failed: {error.__class__.__name__}"
            ) from None

        deadline = time.monotonic() + timeout_seconds
        while server.callback_code is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PkceError("OpenRouter authorization timed out")
            server.timeout = min(1.0, remaining)
            server.handle_request()
        callback_code = server.callback_code
    finally:
        server.server_close()
    return exchange(callback_code, verifier, transport=transport)


def reject_off_origin(url, what="endpoint"):
    """Public guard so callers can pre-check any provider-supplied URL."""
    _assert_allowed_origin(url, what)
