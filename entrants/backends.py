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

MEASUREMENT STATUS (re-probed 2026-09-06, entrant lane).

The original line read: "cli and api are implemented and UNMEASURED here - no
key was used and no spend was incurred building this." It is quoted rather than
deleted because most of it was TRUE and an earlier pass at this docstring
overcorrected. Split by clause:

  "no key was used, no spend was incurred"   TRUE, and still true of cli.
        Every cli match ran on local Ollama weights or on a prepaid
        subscription CLI. Neither uses an API key; neither has a marginal cost
        per match. The arena's $0-per-match property was never violated.

  "cli is UNMEASURED"                        NOT accurate since 2026-08-14.
        The cli backend has been exercised against real models in 16
        transcripts: 8 in matches/ollama/, 3 in matches/cheap-vs-expensive/,
        2 in matches/cross-model-20260829/smoke/ and 3 in matches/model/.
        Spot-checked 2026-09-06: those transcripts still replay-verify PASS
        under the current engine, and 49 of 51 recorded moves carry
        source=model rather than a fallback. parsing.py's own docstring
        records a harness defect that only surfaced when a real model replaced
        the stub, which is not something an unexercised backend can do.

  BUT no valid CROSS-MODEL result exists anywhere in this repo.
        Exercised is not the same as concluded, and the difference is the
        whole point of the quality gate. matches/cross-model-20260829/ stopped
        at that gate with no model result committed (see its SERIES-REPORT.md),
        and the August cheap-vs-expensive series is recorded there as
        fallback-driven and not citable. So "the cli backend has run" and "the
        arena has published a cross-model finding" are different claims, and
        only the first one is true.

  "api is UNMEASURED"                        TRUE until 2026-09-06.
        No transcript in this repo carried an api: backend before that date.
        It is now measured, and it is the first backend here that spends real
        money per match: see matches/openrouter-20260906/.

The separation the rest of this file rests on is unchanged and is the
load-bearing property: a key is read inside the entrant process, from the
entrant's own environment, by NAME, and never crosses the pipe to the engine.
Proved both directions on 2026-09-06 -- without the runner declaring the env
name the key is stripped and the entrant records calls=0 cost_micro_usd=0; with
it, the same seed records source=model and a real cost.
"""

import hashlib
import json
import os
import random
import re
import subprocess
import time


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


# --------------------------------------------------------------------------
# api — the entrant's own key, from the entrant's own environment
# --------------------------------------------------------------------------


class ApiBackend(Backend):
    """HTTP model API using a key the entrant supplies from its own environment.

    Two providers behind one shape. The key is read HERE, in the entrant
    process, by NAME only, and never crosses the pipe to the engine. That is
    the whole point of the `api:` plug point and the reason this arena can host
    a paid entrant without ever holding a credential.

    Spec grammar (parsed in get_backend):

        api:<ENV_VAR>                     Anthropic Messages API, default model
        api:<ENV_VAR>:<model-id>          Anthropic Messages API, named model
        openrouter:<ENV_VAR>:<model-id>   OpenRouter chat/completions

    `max_tokens` defaults PER PROVIDER on purpose. Probed by the studio
    2026-08-07 and re-confirmed here: OpenRouter reasoning models spend their
    budget on hidden reasoning tokens and truncate the VISIBLE answer to an
    empty string when max_tokens is small. The old 256 default would have made
    every reasoning model look like a model that never answers, and the harness
    would have recorded a fallback where the real story was a configuration
    defect. 8000 is the studio's proven floor.

    After every call `last_usage` carries that call's tokens and cost, and the
    running totals feed `usage_note()`. Cost is INTEGER micro-USD, never a
    float: arena/canonical.py refuses to encode a float, so a float reaching a
    transcript note would abort the match.
    """

    kind = "api"

    _PROVIDERS = {
        "anthropic": {
            "url": "https://api.anthropic.com/v1/messages",
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 256,
        },
        "openrouter": {
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "model": "z-ai/glm-5.2",
            "max_tokens": 8000,
        },
    }

    # HTTP statuses worth a second ask. Everything else is a real refusal and
    # retrying it just spends money slower.
    _RETRYABLE = (408, 409, 429, 500, 502, 503, 504)

    def __init__(self, env_var, model=None, provider="anthropic",
                 max_tokens=None, timeout_s=60, retries=2):
        if provider not in self._PROVIDERS:
            raise ValueError("unknown api provider %r" % (provider,))
        defaults = self._PROVIDERS[provider]
        self.provider = provider
        self.env_var = env_var
        self.model = model or defaults["model"]
        self.max_tokens = int(max_tokens or defaults["max_tokens"])
        self.timeout_s = float(timeout_s)
        self.retries = int(retries)
        self.label = "api:%s:%s" % (provider, self.model)
        self.last_usage = {}
        self.calls = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost_micro_usd = 0

    def _build_request(self, key, prompt):
        import urllib.request

        if self.provider == "anthropic":
            body = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            headers = {
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            }
        else:
            body = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "usage": {"include": True},
            }
            headers = {
                "content-type": "application/json",
                "authorization": "Bearer " + key,
                "x-title": "BuilderWars arena entrant",
            }
        return urllib.request.Request(
            self._PROVIDERS[self.provider]["url"],
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
        )

    def _read_response(self, payload):
        """(text, usage) out of a provider response."""
        if self.provider == "anthropic":
            text = "".join(b.get("text", "") for b in payload.get("content", []))
            u = payload.get("usage") or {}
            return text, {
                "prompt_tokens": int(u.get("input_tokens") or 0),
                "completion_tokens": int(u.get("output_tokens") or 0),
                "cost_micro_usd": 0,  # this endpoint does not price the call
            }
        choices = payload.get("choices") or []
        message = (choices[0].get("message") or {}) if choices else {}
        text = message.get("content") or ""
        u = payload.get("usage") or {}
        cost = u.get("cost")
        micro = int(round(float(cost) * 1000000)) if cost is not None else 0
        return text, {
            "prompt_tokens": int(u.get("prompt_tokens") or 0),
            "completion_tokens": int(u.get("completion_tokens") or 0),
            "cost_micro_usd": micro,
        }

    def complete(self, prompt):
        import urllib.error
        import urllib.request

        key = os.environ.get(self.env_var)
        if not key:
            # Names the variable, never the value. This is the error an entrant
            # gets when the runner did not declare the env name in its manifest
            # -- a configuration fault, not a model failure, and worth telling
            # apart from one in the transcript.
            raise RuntimeError(
                "%s is not set in this entrant's environment "
                "(declare the NAME in the manifest 'env' list)" % (self.env_var,)
            )

        payload = None
        last_exc = None
        for attempt in range(self.retries + 1):
            try:
                req = self._build_request(key, prompt)
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code not in self._RETRYABLE:
                    raise RuntimeError("%s HTTP %s" % (self.label, e.code)) from e
                last_exc = RuntimeError("%s HTTP %s" % (self.label, e.code))
            except Exception as e:
                last_exc = e
            if attempt < self.retries:
                time.sleep(1.5 * (attempt + 1))
        if payload is None:
            raise last_exc if last_exc else RuntimeError("%s failed" % (self.label,))

        text, usage = self._read_response(payload)
        self.calls += 1
        self.last_usage = usage
        self.total_prompt_tokens += usage["prompt_tokens"]
        self.total_completion_tokens += usage["completion_tokens"]
        self.total_cost_micro_usd += usage["cost_micro_usd"]
        return text

    def usage_note(self):
        """Compact, canonically-encodable spend summary for a transcript note."""
        return "calls=%d tok_in=%d tok_out=%d cost_micro_usd=%d" % (
            self.calls,
            self.total_prompt_tokens,
            self.total_completion_tokens,
            self.total_cost_micro_usd,
        )


def get_backend(spec, timeout_s=None):
    """Parse a backend spec string.

        stub:v1
        cli:ollama run qwen2.5:7b
        api:ANTHROPIC_API_KEY
        api:ANTHROPIC_API_KEY:claude-haiku-4-5-20251001
        openrouter:OPENROUTER_API_KEY:z-ai/glm-5.2

    Only the NAME of an environment variable ever appears in a spec. The value
    is read inside the entrant process and never leaves it.
    """
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
        env_var, _, model = rest.partition(":")
        return ApiBackend(env_var, model or None, provider="anthropic",
                          timeout_s=timeout_s or 60)
    if kind == "openrouter":
        env_var, _, model = rest.partition(":")
        if not env_var:
            raise ValueError(
                "openrouter backend needs an env var name and a model, e.g. "
                "openrouter:OPENROUTER_API_KEY:z-ai/glm-5.2"
            )
        return ApiBackend(env_var, model or None, provider="openrouter",
                          timeout_s=timeout_s or 60)
    raise ValueError("unknown backend %r; use stub:, cli:, api: or openrouter:" % (spec,))
