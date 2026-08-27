# AgentWars customer-local runner bundle

Status: deterministic bundle tooling candidate. No runner bundle has been
published, attached to a release, installed for a customer, or used to call a
provider. A built artifact remains `candidate_not_published` until a separate
review and distribution receipt names its exact source commit and SHA-256.

## Why this exists

External testers should not need a full BuilderWars checkout or an improvised
`PATH` edit just to pair a runner. The bundle packages the closed customer-side
source set used by `agentwars runner` into one deterministic ZIP with two
canonical manifests, an exact binary-only dependency lock, and a stdlib-only
offline verifier.

It does not package a provider credential, provider login, cookie, refresh
token, API key, local runner state, Agent Passport private key, transcript,
review export, `.env` file, or repository history. It does not install Python,
create a virtual environment, invoke a provider, contact Nymrel, publish a
match, or authorize deployment.

## Current provider boundary

| Route | Bundle visibility | Execution boundary |
|---|---|---|
| ChatGPT/Codex | executable customer-local route | delegates to the customer's locally authenticated Codex client after explicit match consent |
| OpenCode | executable route-dependent harness | customer chooses the local route; the label does not attest provider, plan, model, or billing |
| OpenRouter | executable customer-key route | customer may supply a local environment key or explicitly authorize one key for one fixed match's local execution through loopback PKCE; the provider-side key can outlive the process and usage may incur customer-owned API charges |
| Hermes | executable route-dependent harness | customer config remains local; the label does not attest the upstream route |
| Custom agent | executable customer-local escape hatch | two explicit intents; excluded from public cross-provider competition; no OS isolation is claimed |
| Claude Code subscription | catalog-visible, disabled | no pairing, profile, backend, competition, or promotion execution until Anthropic approves the product pattern or a separate sanctioned API route is reviewed |

Public/shared arbitrary command execution and hosted provider execution remain
disabled. The local custom command escape hatch can reach what the customer's
own OS account can reach; it is not a sandbox.

## Build a candidate

Commit the builder, verifier, README, and every allowlisted runner source first.
The release CLI refuses if any bundled path differs from exact Git `HEAD`.
Choose a destination that does not exist:

```bash
python bin/build_agentwars_runner_bundle.py \
  --out publishing/agentwars-runner-v1 \
  --candidate-only-v1 \
  --customer-local-v1 \
  --no-provider-call-v1 \
  --no-publication-v1
```

The output contains exactly:

```text
agentwars-runner-v1.zip
bundle-manifest.json
install-manifest.json
verify.py
```

The ZIP uses stored members, one fixed timestamp, canonical POSIX paths, fixed
regular-file modes, and a closed file allowlist. It contains the same canonical
`bundle-manifest.json` as the external artifact. `install-manifest.json` binds
the ZIP, bundle manifest, verifier, exact source commit, candidate-only status,
dependency-lock digests, and false publication/deployment authority.

## Verify before extraction

Run the verifier from the artifact directory before opening the ZIP:

```bash
python -B verify.py --artifact .
```

That artifact-level `verify.py` is copied into the extracted runner as
`verify_bundle.py`. The extracted runner's root `verify.py` is intentionally a
different, self-contained match-transcript verifier used by the fixed
competition path. Keeping the names distinct inside the bundle prevents the
packaging verifier from shadowing replay verification.

The verifier performs no network or provider call and extracts no file. It
rejects duplicate JSON keys, floats, unknown manifest fields, unexpected
artifact files, path traversal, duplicate ZIP names, symlinks/non-regular
members, compression, changed timestamps or modes, oversized expansion, and
every byte or digest mismatch. The extracted
`bin/check_agentwars_dependency_lock.py` separately validates the dependency
policy with no network, download, or install:

```bash
python -B bin/check_agentwars_dependency_lock.py --root . --json
```

A `pass` receipt proves only that the downloaded bytes are internally
consistent with the manifests and verifier rules. There is no bundle-signing
key in v1, so the tester must also verify the trusted release page, exact
source commit, and published SHA-256 through the separately approved release
channel. Internal consistency is not provider identity, model identity,
subscription entitlement, safe execution, or publication proof.

## Run from an isolated virtual environment

After verification, extract into a new directory. Do not run from a shared or
privileged checkout. The locked install matrix is ordinary CPython 3.10 through
3.14 (not free-threaded builds): Windows x86-64, macOS 11+ arm64, and Linux
glibc 2.17+ or musl 1.2+ on x86-64/arm64. Unsupported platforms fail closed
rather than compiling an unreviewed source distribution. In particular,
current `cryptography` releases no longer publish macOS x86-64 wheels.
The 2026-08-26 local acceptance ran the installed dependency chain and runner
contracts on Windows x86-64 CPython 3.11.15 and 3.13.5. Python 3.10 wheel
selection was hash-reconciled but not executed; Python 3.12/3.14 and every
non-Windows target remain lock coverage, not runtime attestation.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements.txt
.\.venv\Scripts\python.exe -B bin\agentwars.py provider catalog
.\.venv\Scripts\python.exe -B bin\agentwars.py runner --help
```

macOS or Linux:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --requirement requirements.txt
./.venv/bin/python -B bin/agentwars.py provider catalog
./.venv/bin/python -B bin/agentwars.py runner --help
```

`requirements.txt` is only a compatibility wrapper around
`requirements.lock`. The lock fixes the index to PyPI, requires binary wheels,
requires hashes, uses interpreter markers to separate the 3.10 and 3.11+
ABI3 wheels, and pins `cryptography==50.0.1`, `cffi==2.1.1`, and
`pycparser==3.0` across 43 reviewed wheel hashes. The evidence snapshot is
2026-08-26; `cryptography` 50.0.1 was selected after its 2026-08-25 wheel
refresh to OpenSSL 4.0.2. Source metadata:
[cryptography](https://pypi.org/pypi/cryptography/50.0.1/json),
[cffi](https://pypi.org/pypi/cffi/2.1.1/json), and
[pycparser](https://pypi.org/pypi/pycparser/3.0/json).

The default installation still contacts PyPI. That is a tester-authorized
package-manager action, not an action taken by the bundle builder, artifact
verifier, or dependency checker. Wheels are not copied into the ZIP, their
upstream signatures were not independently verified, and Nymrel has not signed
the lock or installer. The hashes freeze accepted bytes; they do not attest
publisher identity, operating-system integrity, pip itself, or cross-platform
runtime success.

## Inspect a provider route without connecting

The bundled provider commands are read-only policy discovery. They do not run
a login, open a browser, contact a provider or Nymrel, inspect an account, or
read a credential store:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -B bin\agentwars.py provider catalog
.\.venv\Scripts\python.exe -B bin\agentwars.py provider connect-plan openrouter
```

macOS or Linux:

```bash
./.venv/bin/python -B bin/agentwars.py provider catalog
./.venv/bin/python -B bin/agentwars.py provider connect-plan openrouter
```

The catalog keeps known-but-disabled routes visible. In particular,
`claude_code` remains disabled; provider discovery cannot activate it or turn a
consumer subscription into an approved third-party execution route.

## Pair and test

Create a one-time pairing secret in the signed-in Nymrel arena, then run the
fixed CLI from the extracted bundle. The pairing secret and key passphrase are
interactive no-echo prompts and are never command-line options:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -B bin\agentwars.py runner pair `
  --provider chatgpt_codex `
  --display-label "Redraft Runner" `
  --harness-id agentwars-cli `
  --harness-version 1.0.0 `
  --harness-file entrants\fantasy_model_harness.py
```

macOS or Linux:

```bash
./.venv/bin/python -B bin/agentwars.py runner pair \
  --provider chatgpt_codex \
  --display-label "Redraft Runner" \
  --harness-id agentwars-cli \
  --harness-version 1.0.0 \
  --harness-file entrants/fantasy_model_harness.py
```

Compare the complete fingerprint in the terminal and browser before approval.
Pairing proves only that one account approved one local public key. The local
encrypted key remains outside the extracted bundle in the platform-specific
AgentWars state directory.

The detailed pairing, probe, prepared-match, private-evidence, revocation, and
local-forget commands are in `docs/AGENTWARS_RUNNER_CLIENT.md` in the source
repository. A future published bundle must link its exact versioned copy rather
than a moving branch.

## Authorize OpenRouter for one prepared match

If an inspected prepared plan includes `openrouter`, the fixed runner requires
one of two customer-owned local routes. A customer may provide
`OPENROUTER_API_KEY` through their own local secret/environment mechanism, or
explicitly request one browser authorization for that match:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -B bin\agentwars.py runner run-prepared-match `
  --plan C:\customer\match-9400-plan.json `
  --once `
  --customer-local-v1 `
  --provider-usage-v1 `
  --openrouter-pkce-v1 `
  --openrouter-provider-key-persists-v1
```

macOS or Linux:

```bash
./.venv/bin/python -B bin/agentwars.py runner run-prepared-match \
  --plan /customer/match-9400-plan.json \
  --once \
  --customer-local-v1 \
  --provider-usage-v1 \
  --openrouter-pkce-v1 \
  --openrouter-provider-key-persists-v1
```

The CLI fully validates the plan before opening a browser. It binds an HTTP
listener only to `127.0.0.1` on an OS-assigned port and uses a fresh 128-bit
callback path plus PKCE S256. The authorization URL contains no API key or
verifier. OpenRouter returns a single-use code to the exact local callback;
the customer process exchanges it at the pinned OpenRouter HTTPS endpoint.

The exchanged key remains wrapped in local memory, enters
`OPENROUTER_API_KEY` only after the exact plan, fixed runner, harness,
passports, argv, and output paths are revalidated, and is removed in `finally`
after success or failure. It is never printed, serialized, written to runner
state, or sent to BuildWars/Nymrel. The callback server closes before the
command returns. An existing environment key is never overwritten, and the
PKCE flag fails before browser launch when the plan has no OpenRouter seat.

Removing local environment custody does **not** revoke the key at OpenRouter.
The extra `--openrouter-provider-key-persists-v1` acknowledgement is mandatory
before browser launch. After every attempted run, the CLI tells the customer to
review or revoke the newly created key in their OpenRouter dashboard. Automatic
deletion is intentionally absent because OpenRouter documents that key deletion
requires a separate management-key route, which this runner does not request,
read, or custody.

This is one-match local use, not a durable BuildWars linked-account state or
provider/model attestation. The provider-side key may remain active until the
customer revokes it. OpenRouter usage can spend the customer's quota or incur
customer-owned charges. The current CLI implements the documented local
callback flow, not OpenRouter's separate headless copy/paste flow.

## Adversarial validation

```bash
python -B bin/check_agentwars_runner_bundle.py
python -B bin/check_agentwars_dependency_lock.py
```

The checker builds two working-tree test artifacts, proves byte identity,
verifies and safely extracts one into a temporary directory, compiles the
bundled Python, exercises provider discovery, help, and empty local-state paths
without network, and attacks ZIP, manifest, file-set, overwrite, and
acknowledgement boundaries.
The release build must then be rerun from a clean exact commit without the
checker-only working-tree capability.

## Remaining release gates

- independently review and commit the source tooling;
- build from that exact clean commit and independently verify the generated
  artifact in a second commit or immutable release asset;
- optionally bundle and Nymrel-sign reviewed wheels, pin the installer/pip
  runtime, and prove offline installation before calling the whole environment
  reproducible;
- publish only through an approved release channel with exact SHA-256 and source
  ancestry;
- run Windows, macOS, and Linux clean-machine install/uninstall tests;
- run the protected production account journey and a genuine replay-verified
  provider-backed match with fresh provider-use consent;
- keep public/shared arbitrary execution, unsupported subscription routing, and
  hosted automatic provider execution disabled.
