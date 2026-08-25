# AgentWars OpenCode transport and fantasy repair packet

Status: local candidate; not integrated, pushed, deployed, or publicly released.

## Release decision

The parent provider-policy tip `1742226` is withdrawn from release consideration.
Live Ox Alpha MAX evidence exposed a Windows prompt-transport defect that mocked
subprocess tests did not catch. This candidate supersedes that tip and must receive
independent review before integration.

## Fault isolated

On this Windows installation, `shutil.which("opencode")` resolves the npm launcher
`opencode.CMD`. That wrapper forwards arguments through `%*`. Authoritative fantasy
context followed a newline in the positional prompt; during live calls Ox repeatedly
answered as if that JSON context did not exist. The same multiline prompt sent
directly to the package's `opencode.exe` produced a legal context-aware answer.

The diagnosis was reproduced at the same game position:

- npm `.CMD` route: Ox claimed no candidates or `allowed_response_objects` were
  supplied;
- direct packaged `.exe` with the same positional argv: legal player selection;
- stdin also carried the full prompt, but was not adopted because the supported
  OpenCode CLI contract already exposes the message as a positional argument.

The contained adapter resolves OpenCode only from explicit absolute PATH entries
outside the current repository. It prefers a direct `opencode.exe` on Windows,
then the exact binary behind the standard npm wrapper. If a `.CMD` or `.BAT`
launcher cannot be unwrapped, construction fails before the provider child runs.
Ordinary absolute-PATH resolution remains compatible across platforms; unsafe
relative/current-repository PATH entries now fail closed. The legacy OpenCode
backend remains unchanged.

## Fantasy harness containment

The fantasy harness also permits exactly one stateless repair call after an invalid
or illegal live-model answer:

- no retry after an initial backend error;
- no retry for deterministic preseason stubs;
- no rejected model text reflected into the new prompt;
- compact authoritative game context and a closed list of legal response objects;
- at most two attempts total;
- receipt stores source, attempt count, sanitized reason, and truncated response
  digests only;
- raw model output never enters the transcript.

The successful controls below required no repair calls. That is important causal
evidence: direct-binary prompt transport fixed first-pass decisions rather than
merely hiding the defect behind fallbacks.

## Live evidence

### Redraft, seed 9401

Artifact root:
`C:\Users\johns\Desktop\agentwars-evidence\20260825-ox-redraft-direct-exe-9401`

- match id: `6162363e36f9aa7a`
- chain head: `8753b1fcd1f57f0a196b5970be0feec737fa58e2f7005e306222610ee0f8de09`
- transcript SHA-256: `be621e7eca70863d79166c923f649679cfbb53fe931d591721b2ef8495a2c0f4`
- result: Ox Sunday Machine 1781, Ox Future Proof 1578
- accepted source claims: 12 model, 0 fallback, 0 scripted
- attempts: 12 first-attempt, 0 second-attempt
- replay verifier: PASS twice
- raw model-output fields in move records: 0

Same-seed diagnostic progression:

1. withdrawn parent: 1 model claim and 11 fallbacks;
2. retry-only candidate through `.CMD`: 2 model claims and 10 fallbacks;
3. direct-executable candidate: 12 model claims and 0 fallbacks.

### Dynasty, seed 9403

Artifact root:
`C:\Users\johns\Desktop\agentwars-evidence\20260825-ox-dynasty-direct-exe-9403`

- match id: `807161ec70fc6885`
- chain head: `b2113a85a923f4dcd72fc1ed6e623e821d6e1b7e4e7706ae5802ab82520d389c`
- transcript SHA-256: `f2cf2d3612b49a063893498885c3480b273ba897d9b7ef76fd87d51d04559af9`
- result: Ox Future Proof 4722, Ox Sunday Machine 3895
- accepted source claims: 12 model, 0 fallback, 0 scripted
- attempts: 12 first-attempt, 0 second-attempt
- replay verifier: PASS twice
- raw model-output fields in move records: 0

### Rejected Ten Fronts control

Artifact root:
`C:\Users\johns\Desktop\agentwars-evidence\20260825-ox-ten-fronts-9501`

The original 80-move configuration had a theoretical runtime above seven hours.
It was cancelled after 10 legal fallback moves and retained only as diagnostic
evidence. It has no result and is not launch evidence.

## Deterministic validation

`python bin/check_provider_hub.py` passes all ten sections, including:

- six-provider catalog and policy contracts;
- hostile schema and secret-handling cases;
- provider argv/environment mocks;
- Windows npm-shim direct-binary resolution and fail-closed absence;
- one-shot fantasy repair, no retry on backend error, no raw reflection, and
  deterministic fallback;
- arena/provider separation;
- all scale, share, product, Ten Fronts, fantasy, self-check, and verifier parity
  regression ladders;
- 43/43 package-versus-single-file verifier parity.

`python -m py_compile entrants/backends.py entrants/fantasy_model_harness.py
bin/check_provider_hub.py` and `git diff --check` also pass.

## Truth boundary

The transcripts prove the accepted moves, deterministic state transitions, and
results. The entrant receipts claim that all 24 accepted picks across the two
controls came from the configured Ox backend. They do **not** independently prove
the upstream model identity, provider account, subscription route, billing route,
or execution provenance. Both summaries therefore remain
`model_influenced_unattested`, with `modelAttested=false` and
`executionClaimsAttested=false`.

No provider credential, auth file, API-key value, browser login, raw stderr, or raw
model response was written into the repository or transcript. No account, hosted
connection, push, merge, deploy, or public release occurred in this slice.

## Remaining release gate

Independent review must inspect the exact commit range, rerun the full checker,
challenge Windows path resolution and prompt-custody claims, verify both live
replays, and return APPROVE or file-and-line CHANGES_REQUESTED. Only an approved
superseding commit may be considered for integration.

## Ox Alpha MAX read-only review contract

Task: adversarially review the current uncommitted candidate without editing it.

Exact source scope:

- `entrants/backends.py`
- `entrants/fantasy_model_harness.py`
- `bin/check_provider_hub.py`
- `docs/AGENTWARS_PROVIDER_POLICY.md`
- `docs/AGENTWARS_FANTASY_REPAIR_PACKET.md`

Done when the reviewer returns concrete file-and-line findings or an explicit
no-finding verdict covering Windows executable resolution, path spoofing and
TOCTOU risk, positional prompt fidelity, retry bounds, raw-output leakage,
receipt truth, legacy compatibility, and the live-evidence claims above.

Validation floor: inspect the exact diff from `1742226`, examine the relevant
callers and tests, and assess whether `python bin/check_provider_hub.py` exercises
the claimed failure boundaries. Do not treat a passing test or provider receipt
as proof by itself.

Non-goals: no edits, formatting, Git mutation, commit, push, deploy, account or
credential action, browser login, live provider call, or control-plane mutation.

Stop immediately on any attempted mutation, missing repository context, or
inability to produce a substantive review. Pagination/status prose is not a
review result.
