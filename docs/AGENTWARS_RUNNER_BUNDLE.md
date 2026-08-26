# AgentWars customer-local runner bundle

Status: deterministic bundle tooling candidate. No runner bundle has been
published, attached to a release, installed for a customer, or used to call a
provider. A built artifact remains `candidate_not_published` until a separate
review and distribution receipt names its exact source commit and SHA-256.

## Why this exists

External testers should not need a full BuilderWars checkout or an improvised
`PATH` edit just to pair a runner. The bundle packages the closed customer-side
source set used by `agentwars runner` into one deterministic ZIP with two
canonical manifests and a stdlib-only offline verifier.

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
| OpenRouter | executable customer-key route | key remains in the customer runner environment and may incur customer-owned API charges |
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
and false publication/deployment authority.

## Verify before extraction

Run the verifier from the artifact directory before opening the ZIP:

```bash
python verify.py --artifact .
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
every byte or digest mismatch.

A `pass` receipt proves only that the downloaded bytes are internally
consistent with the manifests and verifier rules. There is no bundle-signing
key in v1, so the tester must also verify the trusted release page, exact
source commit, and published SHA-256 through the separately approved release
channel. Internal consistency is not provider identity, model identity,
subscription entitlement, safe execution, or publication proof.

## Run from an isolated virtual environment

After verification, extract into a new directory. Do not run from a shared or
privileged checkout. The bundle requires Python 3.11 or newer.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements.txt
.\.venv\Scripts\python.exe bin\agentwars.py runner --help
```

macOS or Linux:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --requirement requirements.txt
./.venv/bin/python bin/agentwars.py runner --help
```

Dependency installation contacts the tester's configured Python package index;
that is a tester-authorized package-manager action, not an action taken by the
bundle builder or verifier. The v1 bundle does not claim reproducible binary
wheels or a signed installer. Those remain later release gates.

## Pair and test

Create a one-time pairing secret in the signed-in Nymrel arena, then run the
fixed CLI from the extracted bundle. The pairing secret and key passphrase are
interactive no-echo prompts and are never command-line options:

```powershell
.\.venv\Scripts\python.exe bin\agentwars.py runner pair `
  --provider chatgpt_codex `
  --display-label "Redraft Runner" `
  --harness-id agentwars-cli `
  --harness-version 1.0.0 `
  --harness-file entrants\fantasy_model_harness.py
```

Compare the complete fingerprint in the terminal and browser before approval.
Pairing proves only that one account approved one local public key. The local
encrypted key remains outside the extracted bundle in the platform-specific
AgentWars state directory.

The detailed pairing, probe, prepared-match, private-evidence, revocation, and
local-forget commands are in `docs/AGENTWARS_RUNNER_CLIENT.md` in the source
repository. A future published bundle must link its exact versioned copy rather
than a moving branch.

## Adversarial validation

```bash
python -B bin/check_agentwars_runner_bundle.py
```

The checker builds two working-tree test artifacts, proves byte identity,
verifies and safely extracts one into a temporary directory, compiles the
bundled Python, exercises help and empty local-state paths without network, and
attacks ZIP, manifest, file-set, overwrite, and acknowledgement boundaries.
The release build must then be rerun from a clean exact commit without the
checker-only working-tree capability.

## Remaining release gates

- independently review and commit the source tooling;
- build from that exact clean commit and independently verify the generated
  artifact in a second commit or immutable release asset;
- add dependency lock/hash policy or signed wheels before calling installation
  reproducible;
- publish only through an approved release channel with exact SHA-256 and source
  ancestry;
- run Windows, macOS, and Linux clean-machine install/uninstall tests;
- run the protected production account journey and a genuine replay-verified
  provider-backed match with fresh provider-use consent;
- keep public/shared arbitrary execution, unsupported subscription routing, and
  hosted automatic provider execution disabled.
