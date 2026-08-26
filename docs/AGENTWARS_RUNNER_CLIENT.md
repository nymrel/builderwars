# AgentWars customer-local runner client

Status: local release candidate. It is not integrated into canonical main,
connected to a production account, or deployed. The accepted local Nymrel
pairing/probe base now has a feature-flagged deterministic fixture candidate,
and BuilderWars has an additive private competition-evidence submission
candidate. Neither is a deployed provider-execution path. A production-account
signed journey and a genuine model-played production match remain launch gates.

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

## Complete one closed fixture job

The first job path is intentionally narrower than a model competition. With a
paired runner id recorded locally, this command signs one exact poll, validates
the server's complete response contract, computes only the pinned SHA-256
fixture in the current process, and signs one exact result:

```powershell
agentwars runner work `
  --challenge-id CHALLENGE_ID `
  --once
```

`--once` is mandatory. The command prompts for the encrypted-key passphrase
once and stops after one terminal response or one granted fixture. It cannot
launch a subprocess, call a provider or model, read provider credentials, run
an arbitrary harness, or accept server-selected code. The job must match the
locally pinned engine and rules manifests, the paired harness id and digest,
and a client-rederived 32-byte public input commitment. Unknown fields,
withheld-output leakage, changed commitments, or any true execution attestation
fail closed.

The returned `conformance` compares the deterministic output digest with the
server's withheld commitment. Even `conformance: match` is digest conformance
only. Provider account, plan, billing, model, person, runtime, harness
execution, and match execution attestations all remain exactly `false`.

## Submit one existing match for private review

`runner submit-match` polls a separate exact competition evidence job, replays
an already completed customer-local fantasy transcript, validates its summary,
engine snapshot, seats, scores, source claims, and optional signed passports,
then uploads one compressed and digest-bound private evidence bundle:

```powershell
agentwars runner submit-match `
  --challenge-id CHALLENGE_ID `
  --summary-file C:\customer\match-summary.json `
  --transcript-file C:\customer\match\MATCH_ID.jsonl `
  --once `
  --customer-local-v1 `
  --provider-usage-v1 `
  --private-evidence-upload-v1
```

All three consent flags and `--once` are mandatory. The command never launches
a provider, model, subprocess, or arbitrary harness; the customer must first
run and inspect the match locally. It never overwrites or deletes the source
files, and the only accepted server state is `verified_private` with
`not_reviewed_not_published`, ranking ineligible, and all eight attestations
false. Pairing-key possession and replay validity still do not prove causal
provider/model/harness execution.

The complete protocol, compression limits, retry boundary, and remaining
hosted gates are in
[`AGENTWARS_COMPETITION_EVIDENCE_JOB.md`](AGENTWARS_COMPETITION_EVIDENCE_JOB.md).

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
python bin/check_competition_evidence_job.py
python bin/check_provider_hub.py
python bin/check_agent_passport.py
```

`check_agentwars_runner.py` uses only a literal loopback server and temporary
state. Its current 151 checks pin deterministic Python-to-Nymrel Ed25519 and
fixture vectors; attack origins, redirects, response schemas, secret
reflection, state drift, wrong passphrases, replay, commitments, withheld-output
leakage, and argv leakage; execute the signed poll/result CLI journey; and
verify that all trust flags remain false. It makes no live provider or Nymrel
request.

## Remaining release gates

- independently accept and integrate the exact Nymrel match-job candidate and
  this exact CLI candidate;
- replay all atomic Lua transitions against an isolated production-compatible
  Redis service, then keep the match-job feature flag closed until production
  configuration is explicitly approved;
- release the pairing, probe, and fixture routes and confirm that the browser
  exposes the complete server-issued runner id after account approval;
- run a real account create → secret → local claim → fingerprint approval →
  signed probe → signed fixture poll/result → revocation → delete journey;
- run a genuine model-influenced, replay-verified match through that runner;
- implement and externally prove the private competition evidence routes before
  treating `runner submit-match` as hosted;
- keep automated server-assigned provider execution closed until a separate
  long-running lease, cancellation, containment, and duplicate-spend protocol
  is independently accepted;
- keep arbitrary public harness execution disabled until OS-level isolation is
  independently accepted.
