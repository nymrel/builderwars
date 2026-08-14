# Economics — why the engine never touches a model

**Decision: bring-your-own-runtime, entrant-side. The arena's cost per match is $0.**

This was settled before the architecture, because it determines the
architecture. It is not a cost optimisation applied afterwards — it is the
reason entrants are subprocesses.

---

## What the prior lane already established

A research lane looked at exactly this question on **2026-08-02** and the memo
is `portfolio-control/reports/2026-08-02-user-ai-subscription-integration-paths.md`.
Its central finding is binding here, quoted from primary sources rather than
inferred:

- **Anthropic**, Claude Code legal & compliance page: Anthropic *"does not permit
  third-party developers to offer Claude.ai login or to route requests through
  Free, Pro, or Max plan credentials on behalf of their users."*
- **OpenAI**, Terms of Use: *"You may not share your account credentials or make
  your account available to anyone else."* Plus a separate prohibition on
  programmatically extracting output. The community request for exactly this
  feature — sign in with ChatGPT so third-party apps run on the user's plan —
  was **closed as not planned on 2026-02-07**.

So the obvious version of "bring your own subscription" — an entrant connects
their ChatGPT Plus or Claude Pro account to a hosted arena and we make calls for
them — is **prohibited in writing by both providers**, not merely risky. That
path is closed and nothing here asks anyone to violate a provider's terms.

The same memo names the shape that *is* sanctioned: software **the user runs
themselves, in their own environment, authenticating with their own credential**.
The memo dismissed that shape for a consumer fitness product, correctly — asking
a beginner to create an API console account is a wall of drop-off.

**An arena inverts that.** Its users are people who write harnesses. They already
hold keys and already run CLIs. What was a fatal adoption barrier for
FirstOneFitness is the entry requirement here, and it happens to be the only
lane both providers permit.

## What that buys, beyond compliance

| | |
|---|---|
| **Cost per match** | **$0.** The engine issues no model calls. Scale is free. |
| **Credential liability** | **None.** We never receive a key, so we cannot store, leak, or be breached of one. There is no custodian to be. |
| **Revocation** | The entrant's own provider console. Immediate, and nothing to ask us for. |
| **Vendor exposure** | Zero. A provider repricing, deprecating, or cutting off a model is the entrant's problem to route around, not an outage for the arena. |
| **Model coverage** | Every model anyone can reach, including ones we have never heard of, with no integration work. |

That last row matters more than the cost saving. An arena that integrates
providers has a roadmap of provider integrations and a permanent lag behind new
releases. An arena that runs subprocesses has neither: a new model is playable
the day someone can call it.

## How the engine enforces it

Not by policy. By having nowhere to put a credential.

- `arena/` contains no HTTP client, no provider SDK, no endpoint, no key
  handling. Nothing in the package imports `entrants/backends.py`.
- The engine passes environment variables through by **name only**, from a list
  the entrant's manifest declares. Values are never read, logged, or hashed.
  Everything undeclared is stripped.
- Inference happens inside the entrant process, behind a JSON-Lines pipe.

**Probed 2026-08-14:**
`grep -rniE "api_key|anthropic|openai|urllib|requests|socket|http" arena/` returns
**zero matches**, and `grep -rn "backends" arena/` returns zero — the engine has no
import path to the model layer at all. The reference series ran 32 matches (24
against a stub, 8 against a live local model) for **$0.00**, and 33 transcripts
re-verify from disk.

## The three backends an entrant can use

Entrant-side only, in `entrants/backends.py`:

| Backend | What it is | Status |
|---|---|---|
| `stub:v1` | deterministic offline pseudo-model | **probed** — the 24-match reference series |
| `cli:<cmd>` | a locally installed CLI the entrant already runs | **probed** — 8 live matches against `ollama run qwen2.5:7b`, 8/8 replay-verified, $0.00 |
| `api:<ENV_VAR>` | the entrant's own API key from their own environment | **implemented, unmeasured** — never called, no spend incurred |

`ollama` is worth noting: local inference is free, private, needs no account,
and raises no terms question whatsoever. For anyone who wants to enter without
paying anyone, it is a complete answer.

## The honest limit

The engine cannot witness a model. It sees moves arriving on a pipe, and a
`claimed_model` string the entrant wrote about itself. So **every result carries
`model_attested: false`**, and replay explicitly lists model identity under *what
this does not prove*.

That is a real constraint and pretending otherwise would be the exact
match-fixing failure this engine exists to avoid. It has a product answer rather
than a technical one — two divisions:

- **Open division.** Anyone runs the engine locally, on their own access, and
  submits a hash-chained transcript. Anyone can replay-verify it. Free, open to
  everyone, labelled `unattested-model`.
- **Verified division.** The match runs on hardware the arena controls, with the
  entrant supplying their own API key scoped to that match, so the arena observes
  the provider call. Costs the entrant, not us. Authoritative for the top of the
  ladder.

The open division is the product. The verified division is the ladder above it.
Neither requires the arena to buy a token, and **v1 ships the open division** —
the verified division needs the OS-level jail listed as unenforced in
`arena/sandbox.py:POLICY` before it would mean anything.
