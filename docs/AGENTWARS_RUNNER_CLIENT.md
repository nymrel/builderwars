# AgentWars customer-local runner client

Status: local release candidate. It is not independently accepted, integrated
into canonical main, connected to a production account, or deployed. The exact
Nymrel web candidate at `b68428f` now includes the matching signed probe route,
but remains a separate local candidate. A production-account signed journey
and a genuine model-played match remain launch gates.

## What this client does

`agentwars runner pair` claims one browser-created, ten-minute pairing secret
with a newly generated Ed25519 public key. The private key stays local as a
passphrase-encrypted PKCS#8 file. A public local profile binds the exact Nymrel
origin, provider catalog mode, harness file digest, public key, and complete
fingerprint.

This creates a signing relationship only. It does not read or move a provider
credential, provider session, browser cookie, refresh token, account password,
or model response. It does not attest a provider account, subscription plan,
billing route, model, person, runtime, harness execution, or match execution.
Every corresponding local profile flag remains exactly `false`.

The older `buildwars_provider pair-keygen` HMAC envelope remains a separate v1
contract. The Ed25519 account-pairing client is additive; it does not silently
reinterpret or downgrade historical envelopes.

## Install and expose the command

From this repository:

```powershell
python -m pip install -r requirements.txt
$env:Path = "$(Resolve-Path .\bin);$env:Path"
agentwars runner --help
```

On POSIX, add `bin/` to `PATH`; the `agentwars` launcher invokes Python 3.
Windows uses `agentwars.cmd`.

## Pair one local runner

1. Sign in to the Nymrel BuilderWars arena.
2. Create a one-time pairing secret in the browser.
3. Run the command below. The secret and key passphrase are prompted with echo
   disabled. There is intentionally no secret or passphrase argument or
   environment-variable route.

```powershell
agentwars runner pair `
  --provider chatgpt_codex `
  --display-label "Redraft Runner" `
  --harness-id agentwars-cli `
  --harness-version 1.0.0 `
  --harness-file entrants/fantasy_model_harness.py
```

The client hashes the exact regular, non-symlink harness file; derives the
provider connection mode from the closed six-provider catalog; reuses the same
encrypted key after an ambiguous response; sends the one-time secret only in
the exact JSON body of `POST /api/builderwars/runners/pairing/claim`; and
requires the exact response schema, challenge id, full fingerprint, state, and
HTTP status to agree.

Compare every four-character group of the 64-character fingerprint shown in
the terminal and browser. Confirm only an exact match.

## Record the browser-issued runner id

After browser confirmation, copy the public `awr1_...` id and record it:

```powershell
agentwars runner activate `
  --challenge-id CHALLENGE_ID `
  --runner-id awr1_PUBLIC_RUNNER_ID
```

The local client labels this id `owner-entered and unverified`. Merely typing
an id cannot establish account approval or an active server record. The signed
probe still has to load the current active key and accept the exact signature.

List public local state without decrypting a key:

```powershell
agentwars runner list
```

## Probe the active signing key

The dedicated probe signs the exact body `{"probe":1}` for the exact path
`/api/builderwars/runners/probe`, requires HTTP 200, and validates the complete
response schema, runner id, fingerprint, request-body digest, evidence class,
and every false attestation. It does not persist a stronger local trust state;
each run uses a fresh timestamp and nonce.

```powershell
agentwars runner probe `
  --challenge-id CHALLENGE_ID
```

An accepted probe is evidence only that the configured server accepted
possession of the active local Ed25519 key. It does not attest a provider
account, subscription, billing route, model, person, runtime, harness
execution, or match execution.

## Sign one exact request

The client hashes and sends the same bounded UTF-8 JSON object bytes. It does
not reserialize them. Floats, non-finite values, duplicate keys, non-object
roots, query strings, redirects, and bodies above 65,536 bytes fail closed.
Every method requires a non-empty JSON object body; use a file containing `{}`
when an exact `DELETE` route has no other fields.

```powershell
agentwars runner request `
  --challenge-id CHALLENGE_ID `
  --method POST `
  --path /EXACT_RELEASED_SIGNED_ROUTE `
  --body-file request.json `
  --response-out response.json
```

The signature covers, in order:

```text
agentwars.runner_request.v1
method:POST
path:/exact/path
body-sha256:<sha256 of exact body bytes>
timestamp:<UTC with exactly milliseconds>
nonce:<16 random bytes as unpadded base64url>
runner-id:<exact awr1 id>
```

The frozen Nymrel TypeScript builder ends this canonical string with exactly
one LF byte. The Ed25519 signature is unpadded base64url and travels in the
five `agentwars-*` headers alongside `Content-Type: application/json`.

Do not replay an ambiguous signed request byte-for-byte. Rerun the CLI command
to create a fresh timestamp, nonce, canonical string, and signature while
keeping the exact method, path, and body. The server may reject reused nonces.

The command never prints a response body. It reports the HTTP status, byte
count, and SHA-256, and writes the body only to a new explicit path. A `2xx`
response is transport evidence; the CLI cannot independently attest that a
server route used the verifier, and it never proves model execution.

## Local custody and crash behavior

Default state lives outside the repository:

- Windows: `%LOCALAPPDATA%\Nymrel\AgentWars\runners`
- macOS: `~/Library/Application Support/Nymrel/AgentWars/runners`
- Linux: `$XDG_DATA_HOME/nymrel/agentwars/runners`, or the standard local data
  fallback

Each challenge has one encrypted key file and one exact-schema public profile.
Mutations take an OS file lock. Profile updates write a same-directory
temporary file, flush it, atomically replace the prior profile, and fsync the
directory where the platform supports it. POSIX paths fail closed when owned
by another user or accessible to group/other users.

Windows ACL strength is not inferred from `chmod`; passphrase encryption is
the confidentiality boundary there. Python cannot guarantee zeroization of
immutable prompt strings, OS swap, or crash dumps. Malware or an administrator
already acting as the same user can defeat local custody. These limits are not
called secure isolation.

If a claim response is lost, rerun `pair` with the same secret, arguments, and
passphrase. The client reuses the exact key and profile. It never rotates the
candidate behind a used pairing secret. A different label, provider, origin,
harness version, or harness digest is refused as metadata drift. The secret is
not persisted, so a process restart requires the customer to enter it again.

If the browser reaches confirmation but the CLI never received its claim
response, the owner may still record the browser-issued runner id. The profile
retains `serverClaimStatus: not_confirmed` and labels that id unverified; only a
later signed request accepted by the active-key verifier can settle the
transport ambiguity. An interruption can therefore leave encrypted local
state even before the CLI prints success. Inspect `agentwars runner list`
(using the same `--state-dir`, if supplied) before retrying.

## Network policy

Production is pinned to exact `https://nymrel.com`: no alternate casing,
explicit port, userinfo, path, query, fragment, proxy, or redirect. Local tests
may use exact literal `127.0.0.1` or `[::1]` origins. `localhost`, IP shorthand,
and non-loopback cleartext are refused. TLS uses the system trust store with a
minimum of TLS 1.2; public-key pinning is not claimed.

## Delete local custody

```powershell
agentwars runner forget --challenge-id CHALLENGE_ID
```

The command requires typing `DELETE` unless `--yes` is supplied. It removes
only the exact encrypted key and public profile. Deletion is irreversible but
is not secure erasure on journaling or solid-state storage. It does not revoke
the server record; revoke that separately in the authenticated browser.

## Validation

```powershell
python bin/check_agentwars_runner.py
python bin/check_provider_hub.py
python bin/check_agent_passport.py
```

`check_agentwars_runner.py` uses only a literal loopback server and temporary
state. It pins a deterministic Python-to-Nymrel Ed25519 vector; attacks origin
spellings, redirects, response schemas, secret reflection, state drift, wrong
passphrases, replay, and argv leakage; and verifies that all trust flags remain
false. It makes no live provider or Nymrel request.

## Remaining release gates

- independently review and integrate the exact Nymrel `b68428f` web tip and
  the exact CLI tip;
- release the candidate signed probe route and confirm that the browser exposes
  the complete server-issued runner id after account approval;
- run a real account create → secret → local claim → fingerprint approval →
  signed request → revocation → delete journey;
- run a genuine model-influenced, replay-verified match through that runner;
- keep arbitrary public harness execution disabled until OS-level isolation is
  independently accepted.
