"""Model backends — ENTRANT SIDE ONLY.

Nothing in the `arena` package imports this file, and nothing here is reachable
from the referee. That separation is the whole economic and legal argument:

  * The engine never holds a credential, so it cannot leak one.
  * The engine never buys a token, so a match costs the arena nothing.
  * Inference runs in the entrant's own environment, under the entrant's own
    account, which is the shape both Anthropic and OpenAI permit. Routing a
    user's consumer subscription through a hosted service is prohibited in
    writing by both; running software yourself against your own access is not.

Three backends:

  stub:<name>       deterministic offline pseudo-model. Free, reproducible, and
                    what the reference matches use, so the demo needs no
                    account and no spend.
  cli:<command>     shell out to a CLI the entrant already has installed and
                    signed in (claude, codex, gemini, ...). This is prepaid
                    subscription capacity used by the person who holds it.
  api:<ENV_VAR>     the entrant's own API key from their own environment.

`stub` is probed by the reference matches. `cli` and `api` are implemented and
UNMEASURED here — no key was used and no spend was incurred building this.
"""

import hashlib
import json
import os
import random
import re
import shutil
import subprocess


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
# cli — prepaid subscription capacity, run by the person who holds it
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


def get_backend(spec, timeout_s=None):
    """Parse a backend spec string used wholly inside an entrant process."""
    kind, _, rest = spec.partition(":")
    if kind == "stub":
        return StubBackend(rest or "v1")
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
