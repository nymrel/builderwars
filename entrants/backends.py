"""Model backends — ENTRANT SIDE ONLY.

Nothing in the `arena` package imports this file, and nothing here is reachable
from the referee. That separation is the whole economic argument:

  * The engine never holds a credential, so it cannot leak one.
  * The engine never buys a model token. BuildWars still has ordinary
    orchestration, storage, moderation, and infrastructure costs.
  * Inference runs in the entrant's own environment, under the entrant's own
    account. BuildWars states no plan entitlement or permission beyond current
    provider documentation; customers are responsible for their own provider
    terms.

Three legacy backends (unchanged specs):

  stub:<name>       deterministic offline pseudo-model. Free, reproducible, and
                    what the reference matches use, so the demo needs no
                    account and no spend.
  cli:<command>     shell out to a CLI the entrant already has installed and
                    signed in (claude, codex, gemini, ...). Its auth and billing
                    method remain the entrant operator's responsibility.
  api:<ENV_VAR>     the entrant's own API key from their own environment.

Provider-backed adapters (BuildWars provider hub) build one adapter per catalog
provider on the same rule — the entrants' own machine, the entrants' own
account — with hardened child environments: common API-key environment
variables are removed from subscription-intent children to reduce accidental
API billing, raw child stderr and response bodies never enter raised errors, and
redirects are refused so authorization cannot be forwarded off-origin.
``get_provider_backend`` maps a catalog id to one of them. None of them ever
receive a credential from BuildWars; every one reads its auth state from the
local machine it runs on.

Runtime intent capability (fail closed):

  Constructing any provider adapter, or any non-stub legacy backend through
  ``get_backend``, requires an explicit ``customer_local_v1`` runtime intent
  capability (returned by ``acknowledge_customer_local_v1()``). ``custom_agent``
  additionally requires a second explicit opt-in
  capability (returned by ``acknowledge_unsafe_custom_command()``); without
  both exact objects construction fails before any subprocess is resolved.
  Capabilities travel through the construction call instead of ambient process
  state. They record intent ONLY: they are not an OS isolation boundary and
  grant no sandboxing. Machine policy twin:
  docs/AGENTWARS_PROVIDER_POLICY.v1.json.

Child environments are built from a fixed allowlist of OS/runtime path and
locale variables — never ``dict(os.environ)``. Host API keys, tokens, cloud
credentials, proxy credentials, and arbitrary host variables cannot reach a
provider child. Process-local extra variables are restricted to the exact
OpenCode containment keys and validated before use.

`stub` is probed by the reference matches. `cli`, `api`, `opencode` are
implemented and UNMEASURED here — no key was used and no spend was incurred
building this. The provider adapters are likewise UNMEASURED contracts:
argv/env shapes verified against mocked subprocesses and networks only.
"""

import hashlib
import json
import math
import os
import random
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request


# --------------------------------------------------------------------------
# explicit runtime-intent capabilities (not an isolation boundary)
# --------------------------------------------------------------------------


REQUIRED_RUNTIME_INTENT = "customer_local_v1"

_CUSTOMER_LOCAL_V1_INTENT = object()
_UNSAFE_CUSTOM_COMMAND_INTENT = object()


def acknowledge_customer_local_v1():
    """Return the explicit customer-local runtime-intent capability.

    The object records INTENT ONLY: it is not an OS isolation boundary, it
    sandboxes nothing, and it authorizes nothing beyond the construction call
    that explicitly receives it. See docs/AGENTWARS_PROVIDER_POLICY.md.
    """
    return _CUSTOMER_LOCAL_V1_INTENT


def acknowledge_unsafe_custom_command():
    """Return the second capability required for ``custom_agent``.

    The custom command runs an arbitrary customer-declared argv with far more
    reach than any single-provider adapter, so it needs its own consent in
    addition to ``customer_local_v1`` intent.
    """
    return _UNSAFE_CUSTOM_COMMAND_INTENT


def _require_runtime_intent(runtime_intent, what):
    if runtime_intent is not _CUSTOMER_LOCAL_V1_INTENT:
        raise RuntimeError(
            f"{what} requires the 'customer_local_v1' runtime intent "
            "capability; call acknowledge_customer_local_v1() and pass its "
            "return value (or use --customer-local-v1). This records local "
            "customer custody only and is not an OS isolation boundary."
        )


def _require_custom_command_opt_in(unsafe_custom_command_intent):
    if unsafe_custom_command_intent is not _UNSAFE_CUSTOM_COMMAND_INTENT:
        raise RuntimeError(
            "custom_agent requires a second explicit unsafe-local-command "
            "capability; call acknowledge_unsafe_custom_command() and pass "
            "its return value (or use --unsafe-custom-command). Default "
            "construction refuses to resolve any subprocess."
        )


# --------------------------------------------------------------------------
# child environment policy — closed path/config/locale/TLS allowlist
# --------------------------------------------------------------------------


CHILD_ENV_ALLOWLIST = (
    "APPDATA",
    "ANTHROPIC_CONFIG_DIR",
    "CLAUDE_CONFIG_DIR",
    "CODEX_HOME",
    "COLORTERM",
    "COMSPEC",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "HERMES_HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "LOCALAPPDATA",
    "NODE_EXTRA_CA_CERTS",
    "NO_COLOR",
    "OPENCODE_CONFIG_DIR",
    "PATH",
    "PATHEXT",
    "REQUESTS_CA_BUNDLE",
    "SHELL",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "SYSTEMROOT",
    "TERM",
    "TEMP",
    "TMP",
    "TMPDIR",
    "TZ",
    "USERPROFILE",
    "WINDIR",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
)

EXTRA_CHILD_ENV_KEYS = frozenset(
    {
        "OPENCODE_AUTO_SHARE",
        "OPENCODE_CONFIG_CONTENT",
        "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS",
        "OPENCODE_DISABLE_EXTERNAL_SKILLS",
        "OPENCODE_DISABLE_PROJECT_CONFIG",
        "OPENCODE_PURE",
    }
)

_MAX_CHILD_ENV_VALUE_BYTES = 65536


def _validated_env_value(name, value):
    """Validate one child value without ever echoing it in an error."""
    if not isinstance(value, str):
        raise TypeError(f"child env {name} must be a string")
    encoded = value.encode("utf-8")
    if not encoded:
        raise ValueError(f"child env {name} must not be empty")
    if len(encoded) > _MAX_CHILD_ENV_VALUE_BYTES:
        raise ValueError(
            f"child env {name} exceeds {_MAX_CHILD_ENV_VALUE_BYTES} bytes"
        )
    if "\x00" in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"child env {name} contains control characters")
    return value


def _validated_extra_env(extra_env):
    """Validate process-local extra child-environment entries.

    Only the exact OpenCode containment keys are accepted. This prevents a
    caller from smuggling a token, proxy, loader hook, or arbitrary host value
    into a provider process under a plausible-looking variable name.
    """
    if extra_env is None:
        return None
    if not isinstance(extra_env, dict):
        raise TypeError("extra env must be a dict of names to string values")
    out = {}
    for key, value in extra_env.items():
        if key not in EXTRA_CHILD_ENV_KEYS:
            raise ValueError("extra child env name is not in the closed allowlist")
        out[key] = _validated_env_value(key, value)
    return out


class Backend:
    kind = "abstract"
    label = "abstract"

    def complete(self, prompt: str) -> str:
        raise NotImplementedError


# --------------------------------------------------------------------------
# stub
# --------------------------------------------------------------------------


class StubBackend(Backend):
    """A deterministic stand-in for a weak model.

    Reads the position out of the prompt the way a model would, then answers in
    prose. Usually picks a legal but strategically arbitrary move. Sometimes it
    rambles without answering, and sometimes it names a move that is not
    available — because real models do both, and a harness's job is to cope.

    Deterministic in the prompt, so a match against it reproduces exactly.
    """

    kind = "stub"

    def __init__(self, name="v1"):
        self.label = f"stub:{name}"
        self._name = name

    def complete(self, prompt: str) -> str:
        seed = hashlib.sha256((self._name + "\x1f" + prompt).encode("utf-8")).digest()
        rng = random.Random(int.from_bytes(seed[:8], "big"))

        m = re.search(r"heaps:\s*\[([0-9,\s]*)\]", prompt)
        heaps = [int(x) for x in m.group(1).split(",") if x.strip()] if m else []
        roll = rng.random()

        if not heaps:
            return "I need to see the board before I can move."
        if roll < 0.12:
            return (
                "Let me think about this position. There are a few directions here and "
                "the balance looks delicate, so I want to weigh them before committing."
            )
        if roll < 0.22:
            # Names a move that is not available. A validating harness catches it.
            bad_heap = len(heaps) + rng.randint(0, 1)
            return f"I'll take 2 from heap {bad_heap}."

        live = [i for i, h in enumerate(heaps) if h > 0]
        if not live:
            return "The board looks empty to me."
        i = rng.choice(live)
        take = rng.randint(1, heaps[i])

        # Answer in prose OR as a bare JSON object. Real models do both, and a
        # stub that only ever emitted prose is what let a parsing defect survive
        # the whole stub series undetected — the fixture was reflecting the shape
        # I had imagined rather than testing for the ones that occur.
        if rng.random() < 0.4:
            return json.dumps({"heap": i, "take": take})
        return f"Looking at the heaps, I'll take {take} from heap {i}."


# --------------------------------------------------------------------------
# cli — local CLI capacity; auth and billing are chosen by its operator
# --------------------------------------------------------------------------


class CliBackend(Backend):
    """Send the prompt to a locally installed, already-signed-in CLI.

    UNMEASURED in this build. The command is whatever the entrant names, so the
    arena neither sees nor stores any credential.
    """

    kind = "cli"

    # 60s was the old default and it silently corrupted a result: running a 3B
    # and a 14B model in the same series made ollama evict and cold-reload the
    # small one, which pushed its first call past 60s. The call raised, the
    # solver harness fell back to its own computed move, and the series looked
    # like "the small model won" when the small model had never answered.
    # A backend timeout is a property of the machine, so it has to be tunable.
    def __init__(self, command, timeout_s=300):
        self.command = command if isinstance(command, list) else command.split()
        self.timeout_s = timeout_s
        self.label = f"cli:{self.command[0]}"

    def complete(self, prompt: str) -> str:
        proc = subprocess.run(
            self.command,
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout_s,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"{self.label} exited {proc.returncode}: "
                f"{proc.stderr.decode('utf-8', 'replace')[:400]}"
            )
        return proc.stdout.decode("utf-8", "replace")


class OpenCodeBackend(Backend):
    """Use an already-authorized OpenCode model and return only its text event.

    JSON event mode keeps OpenCode's transport envelope out of the fantasy
    parser. Tool permissions remain a responsibility of the entrant manifest's
    process-local ``OPENCODE_CONFIG_CONTENT`` policy.
    """

    kind = "opencode"

    def __init__(self, model, variant="max", timeout_s=300):
        if not model or any(char.isspace() for char in model):
            raise ValueError("opencode backend needs one provider/model identifier")
        if not variant or any(char.isspace() for char in variant):
            raise ValueError("opencode variant must be one token")
        self.model = model
        self.variant = variant
        self.timeout_s = timeout_s
        self.label = f"opencode:{model}@{variant}"

    def complete(self, prompt: str) -> str:
        executable = shutil.which("opencode")
        if executable is None:
            raise FileNotFoundError("opencode is not available on PATH")
        command = [
            executable,
            "run",
            "-m",
            self.model,
            "--variant",
            self.variant,
            "--format",
            "json",
            "--agent",
            "agentwars-entrant",
            "--pure",
        ]
        proc = subprocess.run(
            command,
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout_s,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"{self.label} exited {proc.returncode}: "
                f"{proc.stderr.decode('utf-8', 'replace')[:400]}"
            )
        texts = []
        for line in proc.stdout.decode("utf-8", "replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            part = event.get("part") if isinstance(event, dict) else None
            if (
                isinstance(event, dict)
                and event.get("type") == "text"
                and isinstance(part, dict)
                and isinstance(part.get("text"), str)
            ):
                texts.append(part["text"])
        if not texts:
            raise RuntimeError(f"{self.label} returned no assistant text event")
        return texts[-1].strip()


# --------------------------------------------------------------------------
# api — the entrant's own key, from the entrant's own environment
# --------------------------------------------------------------------------


class ApiBackend(Backend):
    """Anthropic Messages API using a key the entrant supplies.

    UNMEASURED in this build — implemented, never called, no spend incurred.
    The key is read here, in the entrant process, and never crosses the pipe to
    the engine.
    """

    kind = "api"

    def __init__(self, env_var, model="claude-haiku-4-5-20251001", max_tokens=256):
        self.env_var = env_var
        self.model = model
        self.max_tokens = max_tokens
        self.label = f"api:{model}"

    def complete(self, prompt: str) -> str:
        import urllib.request

        key = os.environ.get(self.env_var)
        if not key:
            raise RuntimeError(f"{self.env_var} is not set in this entrant's environment")
        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return "".join(b.get("text", "") for b in payload.get("content", []))


# --------------------------------------------------------------------------
# provider-backed adapters — BuildWars provider hub, customer-owned access
# --------------------------------------------------------------------------


def _argv_token(value, what, max_len=200):
    """Validate a value destined for a child argv vector.

    Rejects empty values, whitespace/control characters, and leading dashes so
    a crafted model name can never masquerade as a CLI flag.
    """
    if not isinstance(value, str) or not value:
        raise ValueError(f"{what} must be a non-empty string")
    if len(value) > max_len:
        raise ValueError(f"{what} exceeds {max_len} characters")
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{what} must be one token without whitespace or control chars")
    if value.startswith("-"):
        raise ValueError(f"{what} must not start with '-'")
    return value


def _provider_timeout(value, default=300):
    """Provider-path timeouts must be finite positive seconds, never bool."""
    if value is None:
        return default
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
        or value > 3600
    ):
        raise ValueError(
            "backend timeout must be a finite number in (0, 3600] seconds"
        )
    return value


def _validated_command(command):
    """Validate an explicit custom-agent JSON argv vector."""
    if not isinstance(command, (list, tuple)) or not command:
        raise ValueError("custom_agent requires a non-empty JSON argv vector")
    if len(command) > 64:
        raise ValueError("custom_agent argv is limited to 64 entries")
    out = []
    total_bytes = 0
    for part in command:
        if not isinstance(part, str) or not part:
            raise ValueError("custom_agent argv entries must be non-empty strings")
        if any(ord(char) < 32 or ord(char) == 127 for char in part):
            raise ValueError(
                "custom_agent argv entries must not contain control characters"
            )
        encoded = part.encode("utf-8")
        if len(encoded) > 4096:
            raise ValueError("custom_agent argv entries are limited to 4096 bytes")
        total_bytes += len(encoded)
        out.append(part)
    if total_bytes > 16384:
        raise ValueError("custom_agent argv is limited to 16384 bytes")
    return out


def _resolve_executable(name):
    executable = shutil.which(name)
    if executable is None:
        raise FileNotFoundError(
            f"{name} is not available on PATH; install it and complete its own "
            f"local login first (see docs/PROVIDER_CONNECTIONS.md)"
        )
    return executable


MAX_PROMPT_BYTES = 65536
MAX_CHILD_OUTPUT_BYTES = 2 * 1024 * 1024


def _prompt_text(prompt, *, argv_limit=False):
    if not isinstance(prompt, str):
        raise TypeError("provider prompt must be a string")
    encoded = prompt.encode("utf-8")
    limit = 20000 if argv_limit else MAX_PROMPT_BYTES
    if not encoded or len(encoded) > limit:
        raise ValueError(f"provider prompt must contain 1..{limit} UTF-8 bytes")
    return prompt


def _build_child_env(extra_env=None):
    """Child environment: allowlisted path/config/locale/TLS vars + extras.

    The child never inherits the parent environment wholesale, so host API
    keys, tokens, cloud credentials, proxy credentials, and arbitrary host
    variables cannot reach a provider child by accident or by injection.
    """
    env = {}
    for name in CHILD_ENV_ALLOWLIST:
        value = os.environ.get(name)
        if value:
            env[name] = _validated_env_value(name, value)
    extra = _validated_extra_env(extra_env)
    if extra:
        env.update(extra)
    return env


def _run_provider_child(argv, *, label, timeout_s, input_text=None,
                        extra_env=None, ephemeral_cwd=True):
    """Run one provider child in an ephemeral cwd with an allowlisted environment.

    The child sees only ``CHILD_ENV_ALLOWLIST`` variables plus validated
    process-local extras, gets stdin only when a prompt is supplied (otherwise
    /dev/null), and its raw stderr is NEVER copied into a raised error — only
    the exit code travels.
    """
    if input_text is not None:
        input_text = _prompt_text(input_text)
    env = _build_child_env(extra_env)
    temporary = (
        tempfile.TemporaryDirectory(prefix="agentwars-provider-")
        if ephemeral_cwd else None
    )
    workdir = temporary.name if temporary is not None else None
    try:
        proc = subprocess.run(
            argv,
            input=input_text.encode("utf-8") if input_text is not None else None,
            stdin=subprocess.DEVNULL if input_text is None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            cwd=workdir,
            env=env,
        )
    finally:
        if temporary is not None:
            temporary.cleanup()
    if proc.returncode != 0:
        raise RuntimeError(
            f"{label} exited {proc.returncode}; child stderr withheld"
        )
    if len(proc.stdout) > MAX_CHILD_OUTPUT_BYTES:
        raise RuntimeError(f"{label} output exceeded size cap")
    return proc.stdout.decode("utf-8", "replace")


class CodexExecBackend(Backend):
    """ChatGPT/Codex via the locally authenticated `codex exec`.

    UNMEASURED contract. Ephemeral scratch cwd (no project files in reach),
    read-only sandbox, git-repo checks skipped so a scratch dir works, no user
    config or rules loaded, ephemeral session. The child environment is the
    fixed path/config/locale/TLS allowlist — no host API-key variable can reach this
    child to trigger accidental API billing; BuildWars still cannot attest the
    auth method cached by Codex. The prompt goes to stdin.
    """

    kind = "codex_exec"

    def __init__(self, timeout_s=300, executable="codex", *, runtime_intent=None):
        _require_runtime_intent(runtime_intent, "chatgpt_codex provider adapter")
        self.executable = _argv_token(executable, "codex executable", 120)
        self.timeout_s = _provider_timeout(timeout_s)
        self.label = "chatgpt_codex:codex exec"

    def argv(self):
        return [
            self.executable,
            "exec",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "-",
        ]

    def complete(self, prompt: str) -> str:
        argv = [_resolve_executable(self.executable)] + self.argv()[1:]
        out = _run_provider_child(
            argv,
            label=self.label,
            timeout_s=self.timeout_s,
            input_text=prompt,
        ).strip()
        if not out:
            raise RuntimeError(f"{self.label} returned no output")
        return out


class ClaudePrintBackend(Backend):
    """Claude Code via locally authenticated non-interactive `claude -p`.

    UNMEASURED contract. One turn, text output, MCP servers strictly disabled
    (--strict-mcp-config with none configured), safe mode, empty tool set, no
    session persistence, no fallback model configured. The child environment
    is the fixed path/config/locale/TLS allowlist — no host API-key variable can reach
    this child to trigger accidental API billing; BuildWars still cannot
    attest the auth method cached by Claude Code. Prompt on stdin.
    """

    kind = "claude_print"

    def __init__(self, timeout_s=300, executable="claude", *, runtime_intent=None):
        _require_runtime_intent(runtime_intent, "claude_code provider adapter")
        self.executable = _argv_token(executable, "claude executable", 120)
        self.timeout_s = _provider_timeout(timeout_s)
        self.label = "claude_code:claude -p"

    def argv(self):
        return [
            self.executable,
            "-p",
            "--output-format",
            "text",
            "--max-turns",
            "1",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--safe-mode",
            "--tools",
            "",
        ]

    def complete(self, prompt: str) -> str:
        argv = [_resolve_executable(self.executable)] + self.argv()[1:]
        out = _run_provider_child(
            argv,
            label=self.label,
            timeout_s=self.timeout_s,
            input_text=prompt,
        ).strip()
        if not out:
            raise RuntimeError(f"{self.label} returned no output")
        return out


class OpenRouterChatBackend(Backend):
    """OpenAI-compatible chat completion against the runner's own key.

    UNMEASURED network contract. Reads OPENROUTER_API_KEY from THIS process's
    environment at call time; the key is placed only into the request header
    and never appears in logs, labels, or exception messages. The default
    transport REFUSES redirects so the Authorization header can never be
    forwarded off-origin, and response bodies are size-capped; failures are
    sanitized to status/class names with no body content.
    """

    kind = "openrouter_chat"

    ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
    PINNED_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
    ENV_VAR = "OPENROUTER_API_KEY"
    MAX_RESPONSE_BYTES = 2 * 1024 * 1024

    def __init__(self, model, timeout_s=300, transport=None, *, runtime_intent=None):
        _require_runtime_intent(runtime_intent, "openrouter provider adapter")
        self.model = _argv_token(model, "openrouter model")
        self.timeout_s = _provider_timeout(timeout_s)
        self._transport = transport
        self.label = f"openrouter:{model}"

    class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        """Refuse every redirect; never re-send Authorization elsewhere."""

        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    _OPENER = urllib.request.build_opener(_NoRedirectHandler)

    @classmethod
    def _default_transport(cls, request, timeout_s):
        import urllib.error

        try:
            with cls._OPENER.open(request, timeout=timeout_s) as response:
                if response.geturl() != cls.PINNED_ENDPOINT:
                    raise RuntimeError("openrouter response origin/path drifted")
                return response.read(cls.MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:
            if 300 <= error.code < 400:
                raise RuntimeError(
                    f"openrouter refused redirect (HTTP {error.code}); "
                    f"authorization is never forwarded off-origin"
                ) from None
            # Status code only — bodies could echo auth context; never risk it.
            raise RuntimeError(f"openrouter HTTP {error.code}") from None

    def complete(self, prompt: str) -> str:
        import urllib.error
        import urllib.request

        key = os.environ.get(self.ENV_VAR)
        if not key:
            raise RuntimeError(
                f"{self.ENV_VAR} is not set in this entrant's environment; "
                f"complete OpenRouter PKCE on your own machine first"
            )
        if (
            not isinstance(key, str)
            or not 16 <= len(key) <= 2048
            or any(ord(ch) < 33 or ord(ch) > 126 for ch in key)
        ):
            raise RuntimeError(f"{self.ENV_VAR} has an unsafe shape")
        if self.ENDPOINT != self.PINNED_ENDPOINT:
            raise RuntimeError("openrouter endpoint does not match the pinned URL")
        prompt = _prompt_text(prompt)
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.ENDPOINT,
            data=body,
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {key}",
            },
            method="POST",
        )
        transport = self._transport or self._default_transport
        try:
            raw = transport(request, self.timeout_s)
        except RuntimeError:
            raise
        except urllib.error.HTTPError as error:
            if 300 <= error.code < 400:
                raise RuntimeError(
                    f"{self.label} refused redirect (HTTP {error.code}); "
                    f"authorization is never forwarded off-origin"
                ) from None
            raise RuntimeError(f"{self.label} HTTP {error.code}") from None
        except Exception as error:
            raise RuntimeError(
                f"{self.label} transport failed: {error.__class__.__name__}"
            ) from None
        if not isinstance(raw, (bytes, bytearray)):
            raise RuntimeError(f"{self.label} transport returned non-bytes")
        raw = bytes(raw)
        if len(raw) > self.MAX_RESPONSE_BYTES:
            raise RuntimeError(f"{self.label} response exceeded size cap")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RuntimeError(f"{self.label} returned malformed JSON") from None
        choices = payload.get("choices") if isinstance(payload, dict) else None
        content = None
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(message, dict):
                content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"{self.label} response missing assistant content")
        return content.strip()


class HermesOneshotBackend(Backend):
    """Hermes via locally authenticated `hermes --oneshot`.

    UNMEASURED contract — live behavior is not measured in this build. The
    official CLI contract takes the prompt as a direct ARGUMENT (never
    stdin-only), with the provider explicit and the model fully qualified as
    ``provider/model``, rules ignored, safe mode on, and only the non-mutating
    ``clarify`` toolset available. No fallback claim: a failed shot raises and
    the harness's deterministic fallback takes over.
    """

    kind = "hermes_oneshot"

    def __init__(self, provider_model, timeout_s=300, executable="hermes", *,
                 runtime_intent=None):
        _require_runtime_intent(runtime_intent, "hermes provider adapter")
        self.executable = _argv_token(executable, "hermes executable", 120)
        if not isinstance(provider_model, str) or "/" not in provider_model:
            raise ValueError("hermes backend needs an explicit 'provider/model' identifier")
        provider, _, model = provider_model.partition("/")
        self.provider = _argv_token(provider, "hermes provider", 80)
        self.model = _argv_token(model, "hermes model", 120)
        self.timeout_s = _provider_timeout(timeout_s)
        self.label = f"hermes:{self.provider}/{self.model}"

    def argv(self, prompt=None):
        """Full argv; when ``prompt`` is given it is appended as the argument."""
        return [
            self.executable,
            "--oneshot",
            "--provider",
            self.provider,
            "--model",
            f"{self.provider}/{self.model}",
            "--ignore-rules",
            "--safe-mode",
            "--toolsets",
            "clarify",
        ] + ([prompt] if prompt is not None else [])

    def complete(self, prompt: str) -> str:
        prompt = _prompt_text(prompt, argv_limit=True)
        argv = [_resolve_executable(self.executable)] + self.argv(prompt)[1:]
        out = _run_provider_child(
            argv, label=self.label, timeout_s=self.timeout_s
        ).strip()
        if not out:
            raise RuntimeError(f"{self.label} returned no output")
        return out


class OpenCodeProviderBackend(Backend):
    """OpenCode PROVIDER path — hardened adapter distinct from legacy specs.

    UNMEASURED contract. Ephemeral cwd, `--pure` (no project config), JSON
    event output, the prompt as a direct positional argument per the official
    CLI contract, and NO `--auto`. The child runs under a process-local
    OPENCODE_CONFIG_CONTENT agent whose tools and permissions are all denied,
    with external/Claude skill loading disabled and project config disabled via
    OPENCODE_DISABLE_PROJECT_CONFIG=1. The user's local auth store is left
    untouched — local auth is exactly what this path delegates to.
    """

    kind = "opencode_run"

    AGENT_NAME = "agentwars-provider"

    @classmethod
    def config_content(cls):
        permission = {
            "*": "deny",
            "bash": "deny",
            "edit": "deny",
            "read": "deny",
            "glob": "deny",
            "grep": "deny",
            "list": "deny",
            "lsp": "deny",
            "webfetch": "deny",
            "websearch": "deny",
            "task": "deny",
            "skill": "deny",
            "question": "deny",
            "external_directory": "deny",
        }
        return json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "default_agent": cls.AGENT_NAME,
                "permission": dict(permission),
                "agent": {
                    cls.AGENT_NAME: {
                        "description": (
                            "BuildWars provider one-shot: answer the prompt, "
                            "touch nothing."
                        ),
                        "mode": "primary",
                        "permission": dict(permission),
                    }
                },
            },
            separators=(",", ":"),
        )

    def __init__(self, model, variant="max", timeout_s=300, *, runtime_intent=None):
        _require_runtime_intent(runtime_intent, "opencode provider adapter")
        model = _argv_token(model, "provider/model identifier")
        provider, separator, provider_model = model.partition("/")
        if not separator:
            raise ValueError(
                "opencode backend needs an explicit 'provider/model' identifier"
            )
        _argv_token(provider, "opencode provider", 80)
        _argv_token(provider_model, "opencode model", 160)
        variant = _argv_token(variant, "variant")
        if "@" in model:
            raise ValueError(
                "pass provider/model without '@'; use the model@variant form"
            )
        self.model = model
        self.variant = variant
        self.timeout_s = _provider_timeout(timeout_s)
        self.label = f"opencode-provider:{model}@{variant}"

    def argv(self, prompt=None):
        return [
            "opencode",
            "run",
            "-m",
            self.model,
            "--variant",
            self.variant,
            "--format",
            "json",
            "--agent",
            self.AGENT_NAME,
            "--pure",
        ] + (["--", prompt] if prompt is not None else [])

    def child_env(self):
        return {
            "OPENCODE_CONFIG_CONTENT": self.config_content(),
            "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
            "OPENCODE_PURE": "1",
            "OPENCODE_AUTO_SHARE": "false",
            "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
            "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
        }

    def complete(self, prompt: str) -> str:
        prompt = _prompt_text(prompt, argv_limit=True)
        executable = shutil.which("opencode")
        if executable is None:
            raise FileNotFoundError(
                "opencode is not available on PATH; run `opencode auth login` "
                "yourself first. A missing binary never means a missing account."
            )
        argv = [executable] + self.argv(prompt)[1:]
        stdout = _run_provider_child(
            argv,
            label=self.label,
            timeout_s=self.timeout_s,
            extra_env=self.child_env(),
        )
        texts = []
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            part = event.get("part") if isinstance(event, dict) else None
            if (
                isinstance(event, dict)
                and event.get("type") == "text"
                and isinstance(part, dict)
                and isinstance(part.get("text"), str)
            ):
                texts.append(part["text"])
        if not texts:
            raise RuntimeError(f"{self.label} returned no assistant text event")
        return texts[-1].strip()


class CustomerCommandBackend(Backend):
    """custom_agent: the customer's OWN prompt/stdout program.

    Truthful scope: this is NOT an arena/1 JSONL entrant slot. The declared
    repeatable JSON argv runs locally, receives the prompt on stdin, and its
    final stdout text is parsed by the calling harness as the answer. A true
    arena/1 entrant is registered directly as a manifest command outside the
    model harness.

    Double-gated: construction requires BOTH the ``customer_local_v1`` runtime
    intent capability AND a second explicit unsafe-local-command capability.
    Default construction fails before any subprocess is resolved.
    """

    kind = "custom_cli"

    def __init__(self, command, timeout_s=300, *, runtime_intent=None,
                 unsafe_custom_command_intent=None):
        _require_runtime_intent(runtime_intent, "custom_agent provider adapter")
        _require_custom_command_opt_in(unsafe_custom_command_intent)
        self.command = list(_validated_command(command))
        self.timeout_s = _provider_timeout(timeout_s)
        self.label = f"custom_cli:{self.command[0]}"

    def complete(self, prompt: str) -> str:
        prompt = _prompt_text(prompt)
        executable = _resolve_executable(self.command[0])
        out = _run_provider_child(
            [executable] + self.command[1:],
            label=self.label,
            timeout_s=self.timeout_s,
            input_text=prompt,
            ephemeral_cwd=False,
        )
        out = out.strip()
        if not out:
            raise RuntimeError(f"{self.label} returned no output")
        return out


PROVIDER_BACKEND_KINDS = (
    "codex_exec",
    "claude_print",
    "opencode_run",
    "openrouter_chat",
    "hermes_oneshot",
    "custom_cli",
)


def get_provider_backend(provider_id, *, model=None, variant=None, command=None,
                         timeout_s=None, runtime_intent=None,
                         unsafe_custom_command_intent=None):
    """Map a BuildWars provider catalog id to an executable entrant backend.

    This is the single source of truth for provider adapter construction; the
    catalog declares which kind serves each provider and this function builds
    exactly that kind. Unknown providers fail closed here as everywhere else.
    Construction requires the explicit ``customer_local_v1`` runtime intent
    capability — and a second explicit capability for ``custom_agent``. Provider-path
    timeouts must be finite positive seconds. ``custom_agent`` builds a
    truthful prompt/stdout command backend from an explicit JSON argv vector —
    it is not an arena/1 slot.
    """
    try:
        from provider_hub.catalog import get_provider
    except ImportError:
        raise RuntimeError(
            "provider hub package unavailable; run from a BuildWars checkout"
        ) from None
    get_provider(provider_id)  # fails closed on unknown ids
    _require_runtime_intent(runtime_intent, f"{provider_id} provider adapter")
    if provider_id != "custom_agent" and unsafe_custom_command_intent is not None:
        raise ValueError(
            "unsafe custom-command intent is valid only for custom_agent"
        )
    effective_timeout = _provider_timeout(timeout_s)
    if provider_id == "chatgpt_codex":
        if model is not None or variant is not None or command is not None:
            raise ValueError("chatgpt_codex does not accept model, variant, or command options")
        return CodexExecBackend(effective_timeout, runtime_intent=runtime_intent)
    if provider_id == "claude_code":
        if model is not None or variant is not None or command is not None:
            raise ValueError("claude_code does not accept model, variant, or command options")
        return ClaudePrintBackend(effective_timeout, runtime_intent=runtime_intent)
    if provider_id == "opencode":
        if command is not None:
            raise ValueError("opencode does not accept a provider command")
        if not model:
            raise ValueError("opencode provider requires --provider-model provider/model")
        return OpenCodeProviderBackend(
            model,
            variant or "max",
            effective_timeout,
            runtime_intent=runtime_intent,
        )
    if provider_id == "openrouter":
        if variant is not None or command is not None:
            raise ValueError("openrouter does not accept variant or command options")
        if not model:
            raise ValueError("openrouter provider requires --provider-model model-id")
        return OpenRouterChatBackend(
            model, effective_timeout, runtime_intent=runtime_intent
        )
    if provider_id == "hermes":
        if variant is not None or command is not None:
            raise ValueError("hermes does not accept variant or command options")
        if not model:
            raise ValueError("hermes provider requires --provider-model provider/model")
        return HermesOneshotBackend(
            model, effective_timeout, runtime_intent=runtime_intent
        )
    if provider_id == "custom_agent":
        if model is not None or variant is not None:
            raise ValueError("custom_agent does not accept model or variant options")
        if command is None:
            raise ValueError(
                "custom_agent requires --provider-command as an explicit JSON "
                "argv vector; a true arena/1 entrant registers directly as a "
                "manifest command outside the model harness"
            )
        return CustomerCommandBackend(
            command,
            effective_timeout,
            runtime_intent=runtime_intent,
            unsafe_custom_command_intent=unsafe_custom_command_intent,
        )
    raise ValueError(f"unknown provider {provider_id!r}")


def execution_claim_for_provider(provider_id):
    """Every provider-backed adapter is a model claim — never attested."""
    try:
        from provider_hub.catalog import get_provider
    except ImportError:
        raise RuntimeError(
            "provider hub package unavailable; run from a BuildWars checkout"
        ) from None
    get_provider(provider_id)  # fails closed on unknown ids
    return "model"


def get_backend(spec, timeout_s=None, *, runtime_intent=None):
    """Parse a backend spec string used wholly inside an entrant process.

    ``stub:`` stays free and intent-free. Every non-stub kind is a real
    execution route and requires the ``customer_local_v1`` runtime intent
    capability.
    """
    kind, _, rest = spec.partition(":")
    if kind == "stub":
        return StubBackend(rest or "v1")
    _require_runtime_intent(runtime_intent, "non-stub legacy backends")
    if kind == "cli":
        if not rest:
            raise ValueError("cli backend needs a command, e.g. cli:claude -p")
        return CliBackend(rest, timeout_s) if timeout_s else CliBackend(rest)
    if kind == "api":
        if not rest:
            raise ValueError("api backend needs an env var name, e.g. api:ANTHROPIC_API_KEY")
        return ApiBackend(rest)
    if kind == "opencode":
        if not rest:
            raise ValueError("opencode backend needs provider/model, optionally followed by @variant")
        model, separator, variant = rest.partition("@")
        return OpenCodeBackend(model, variant or "max", timeout_s or 300)
    raise ValueError(f"unknown backend {spec!r}; use stub:, cli:, api:, or opencode:")


def execution_claim_for_backend(spec):
    """Map a backend declaration to the execution claim bound into a receipt."""
    if not isinstance(spec, str):
        raise ValueError("backend spec must be a string")
    kind, separator, _ = spec.partition(":")
    if not separator:
        raise ValueError("backend spec must include a kind prefix")
    if kind == "stub":
        return "scripted"
    if kind in ("cli", "api", "opencode"):
        return "model"
    raise ValueError(f"unknown backend kind {kind!r}")
