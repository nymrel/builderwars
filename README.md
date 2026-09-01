# BuilderWars

**Same model. Your harness. Re-run every match yourself.**

BuilderWars is the first game inside **AgentWars**: competitive games and sports
where agents enter through an open harness, results are replayable, and the
spectator story never outruns the receipt.

A contest between *harnesses* — the code a person writes around a model — rather
than between vendors. Vendor leaderboards already exist and they mostly measure
whose budget is largest. This measures what a builder did with what they had,
which is a thing a person can get better at.

Home: **<https://nymrel.com/builderwars>**

## Mobile Arena Exchange prototype

The local-only mobile shell turns the platform vision into five working
destinations: Arena, Watch, Compete, Learn, and Build. It renders the tracked,
reviewed Arena receipt corpus through a fail-closed client adapter, retains the
fixed demo fixture as a visibly disclosed fallback, pins and recomputes the
corpus canonical SHA-256 digest before any `verified_corpus` projection, opens
receipt-addressable proofs and receipt-backed rivalry history, saves blueprints only in the browser,
previews future-fixture qualification without execution, separately runs one
deterministic browser-memory Nim exhibition with no model or provider, turns its
receipt candidate into a bounded learning action plus a versioned, still-unplayed
runback, and packages that complete local lineage as a canonical private proof
share. A fresh browser can resolve the embedded receipt, replay, learning, and
runback from the share alone; the `builderwars-local-proof://` locator is not a
public URL, signature, identity, model, provider, registry, ranking, or publication
claim. Every reviewed receipt also offers an optional browser-memory spectator
rehearsal with four explicit states: choose a side or runback, reveal the
already-existing result, verify the exact receipt binding, then enter the
receipt-linked learning path toward a still-unplayed runback. Its choice digest
is not timestamped, collected, graded, counted, ranked, published, or presented
as a prediction. Separately, a reviewed proof can become a still-unplayed runback proposal.
That proposal can be exported as canonical JSON and imported
independently from an empty Receipt Lab for strict local schema and SHA-256
integrity verification. That checksum is
not a signature or origin claim, and import never adopts, qualifies, executes,
ranks, publishes, or spends. A verified import can receive a bounded,
append-only private review decision whose reviewer label remains unattested.
Only `accept_for_blueprint_revision` creates a proposed, uncommitted local
blueprint revision; defer and reject create none. Every review stays hash-linked
in memory and leaves rules, qualification, execution, registry, ranking,
publication, and spending authority absent. The original canonical proposal and
its exact review journal can now be exported together as a bounded canonical
packet and independently reverified from an empty Receipt Lab. Import remains a
memory-only inspection projection: it applies no blueprint and grants no
identity, rules, provider, runner, registry, ranking, publication, or spending
authority. A private correction journal records bounded corrected decisions or
withdrawals against immutable original review digests. Global append links and
per-review supersession links preserve every prior record, while a combined
canonical packet lets a fresh recipient reverify the proposal, original reviews,
corrections, and effective private projection. It cannot rewrite a review,
authenticate a reviewer, apply a blueprint, or grant execution or publication
authority. Two correction packets for the exact same proposal can now be
reverified and carried inside one deterministic private comparison receipt. Its
digest-sorted projection reports shared changed state and one-sided immutable
reviews without choosing a winner, merging histories, resolving a dispute, or
granting any authority. A verified comparison can now be embedded in one
deterministic inspection-learning receipt. Its fixed mapping sends identical
state to rules-binding inspection, changed state to correction-lineage
inspection, and one-sided state to visible-evidence inspection while preserving
Packet A, Packet B, every source digest, and zero correctness, consensus,
approval, progress, blueprint-adoption, or execution authority. The shell
can now turn one exact verified lesson into a deterministic guard-only blueprint
proposal. The fixed mapping offers strict validation, fallback disclosure, or a
human checkpoint; it binds the parent proposal and every source digest, reports
whether the parent carried the current guard value, and remains uncommitted,
unplayed, unqualified, unexecuted, and unpublished with every authority flag
false. One proposal can now be wrapped in a deterministic immutable private
review receipt with accept-for-revision, defer, or reject decisions from fixed
reason codes. Only acceptance creates a local revision candidate, and that
candidate remains uncommitted, unadopted, and unplayed. An accepted review can
now create one versioned local blueprint-revision draft that copies the exact
parent identity, applies only the reviewed allowlisted guard, and preserves
every other guard as carried or explicitly unknown. Defer and reject reviews
cannot create a draft. The draft is canonical and independently reverified from
the accepted review through the complete private inspection ancestry, but it is
still uncommitted, unadopted, unqualified, unplayed, unexecuted, unpublished,
and zero-authority. One verified draft can now receive an immutable private
accept-for-commit-candidate, defer, or reject review. Acceptance creates only an
uncommitted, unadopted local candidate; explicit unknown guard values remain
unknown, force `commitReady: false`, and block commit readiness. Defer and
reject create no candidate. One accepted candidate can now receive a
deterministic local guard-completion proposal. It must supply exactly one
explicit boolean and one bounded identity-unattested provenance code for every
unknown guard, preserve every known and applied guard, and carry the full
verified ancestry. The completed proposal still forces `commitReady: false`
and `requires_guard_completion_review`; it is not a commit, adoption,
qualification, run, registry action, or publication. One verified completion
can now receive an immutable accept-for-commit-review, defer, or reject review.
Only acceptance derives a local candidate for a later operator decision, and
that candidate still forces `commitReady: false`,
`requires_operator_commit_review`, and operator review `not_run`. Defer and
reject derive no candidate. Reviewer identity and guard-value provenance remain
unattested. An accepted completion review can now produce one deterministic
local operator-review packet. The packet binds the exact candidate digest,
reconstructs the original-to-candidate three-guard diff, carries four bounded
validation commands with every evidence status `not_run`, and exposes a
discard-only rollback plus the smallest later operator decision. It does not
record that decision, run validation, mark the candidate commit-ready, commit,
or adopt anything. The shell performs no provider call, inference, account
action, publication, or deployment.

```powershell
python -m http.server 4173 --directory mobile-arena
# open http://127.0.0.1:4173
python bin\check_mobile_arena_read_adapter.py
python bin\check_mobile_arena_qualification.py
python bin\check_mobile_arena_local_exhibition.py
python bin\check_mobile_arena_spectator_rehearsal.py
python bin\check_mobile_arena_learning_runback.py
python bin\check_mobile_arena_portable_runback.py
python bin\check_mobile_arena_portable_review.py
python bin\check_mobile_arena_portable_review_exchange.py
python bin\check_mobile_arena_portable_review_correction.py
python bin\check_mobile_arena_private_review_comparison.py
python bin\check_mobile_arena_private_review_learning.py
python bin\check_mobile_arena_private_blueprint_delta.py
python bin\check_mobile_arena_private_blueprint_delta_review.py
python bin\check_mobile_arena_private_blueprint_revision.py
python bin\check_mobile_arena_private_blueprint_draft_review.py
python bin\check_mobile_arena_private_blueprint_guard_completion.py
python bin\check_mobile_arena_private_blueprint_guard_completion_review.py
python bin\check_mobile_arena_private_blueprint_operator_review_packet.py
python bin\check_mobile_arena_exchange.py
python bin\check_mobile_arena_browser.py
```

The browser gate requires Python Playwright plus its managed Chromium in the QA
environment. It starts an ephemeral `127.0.0.1` server, uses isolated browser
contexts, and closes Chromium and the server before returning. Its real-browser
journeys cover all five destinations, browser history, receipt routes, dialog
focus and Escape restoration, qualification preview, the deterministic local
exhibition through replay-verified receipt candidate, visible learning,
versioned unplayed runback, discard, and reload cleanup, local persistence and
storage denial, schema-invalid source fallback, fatal local-source failure,
reduced motion, service-worker offline reload, responsive widths from 320px to
1040px, accessible names, console/page errors, document overflow, and a strict
same-origin network boundary. Passing it is local browser evidence only; it is
not evidence of hosting, authentication, provider access, live competition,
publication, or production readiness.

The companion Arena read model is compiled from the tracked, reviewed
AgentWars publication artifact. It is deterministic and fail-closed: the build
rejects digest, allowlist, replay, verifier, evidence-label, and generated-file
drift before any result can enter a client read path. The browser adapter also
pins the reviewed digest in executable source and recomputes it with Web Crypto
before projection. Content drift, an internally rehashed but unreviewed model,
or unavailable SHA-256 can never retain the verified-corpus label.

```powershell
python bin\build_mobile_arena_read_model.py --check
python bin\check_mobile_arena_read_model.py
```

`mobile-arena/data/arena-read-model.v1.json` is a local read contract, not a
live or authenticated feed. Its explicit truth boundary keeps model, provider,
runtime, hosting, ranking, and activation claims false until separately proven.
If that contract is missing or invalid, the client discloses `DEMO FALLBACK`;
digest and integrity failures carry bounded fallback reasons without exposing
source contents. If the bounded demo fallback is also unavailable, the shell
fails closed.

Product direction and explicit non-goals:
[`docs/BUILDERWARS_MOBILE_ARENA_EXCHANGE.md`](docs/BUILDERWARS_MOBILE_ARENA_EXCHANGE.md).
Current category research and long-term evidence gates:
[`docs/BUILDERWARS_COMPETITIVE_LANDSCAPE_2026-08-31.md`](docs/BUILDERWARS_COMPETITIVE_LANDSCAPE_2026-08-31.md).

## Measurement contract — schema only

The verified-moment share funnel now uses one strict six-event contract. The
validator accepts exact allowlisted fields and enums, rejects raw URLs, query
strings, person or network identifiers, prompts, output, credentials, duplicate
event ids, and future-dated events, and can produce a deterministic zero
baseline. It has no transport or storage and does not claim instrumentation,
durable counters, users, audience, performance, builder identity, retention, or
launch readiness.

```powershell
python bin\check_agentwars_measurement.py
```

Contract and activation boundary:
[`docs/AGENTWARS_MEASUREMENT_CONTRACT.md`](docs/AGENTWARS_MEASUREMENT_CONTRACT.md).

## Mobile Arena performance budget — local source only

The tracked Mobile Arena shell now has an executable raw-size and deterministic
gzip budget. The gate measures the exact nine-file shell/data set, refuses
missing or unknown assets, attributes per-file and aggregate overruns, and keeps
production timing, real-user experience, hosting, and launch claims false.

```powershell
python bin\check_mobile_arena_performance_budget.py
```

This is a regression budget for reviewed source, not a production speed test or
Core Web Vitals receipt. Contract, limits, and the protected production proof
still required are documented in
[`docs/AGENTWARS_PERFORMANCE_BUDGET.md`](docs/AGENTWARS_PERFORMANCE_BUDGET.md).

## Observability and incident contract — uninstrumented

AgentWars now has a strict ten-event operational schema, deterministic zero
baseline, tamper-resistant in-memory aggregation, and synthetic health, error,
queue, abuse, integrity, secret, deletion, rollback, and support drills. The
decision engine can recommend holds, protected-flow disablement, rollback
assessment, evidence capture, and support routing; it executes none of them.

```powershell
python bin\check_agentwars_observability.py
```

No telemetry sink, alert delivery, status page, staffed support queue,
production threshold, protected flag, or rollback is configured or claimed.
Contract and production activation boundary:
[`docs/AGENTWARS_OBSERVABILITY_INCIDENT_CONTRACT.md`](docs/AGENTWARS_OBSERVABILITY_INCIDENT_CONTRACT.md).

## Retention, deletion, rollback, and recovery — local drills

AgentWars now classifies eight digest-only resource classes, separates simulated
physical deletion from append-only logical suppression, atomically holds
unapproved policy classes, binds rollback to five last-known-good release
dimensions, and injects deletion plus recovery failures. Every request is an
explicit synthetic fixture rather than an identity or consent attestation.

```powershell
python bin\check_agentwars_retention_recovery.py
```

The drills perform no I/O and prove no production data access, deletion,
backup, restore, rollback, deployment, feature-flag change, or operator action.
The exact evidence boundary and protected activation ceremony are documented in
[`docs/AGENTWARS_RETENTION_DELETION_ROLLBACK_RECOVERY.md`](docs/AGENTWARS_RETENTION_DELETION_ROLLBACK_RECOVERY.md).

## Launch threat model — repository-grounded, protected gaps held

BuilderWars now carries an executable public-beta threat model covering the
local browser-authorization gateway, future production Clerk adapter,
multi-tenant hosted reference, signed runner
protocol, customer-local provider authority, entrant process boundary,
publication lineage, deletion/recovery, availability, and release provenance.
It binds ten threats to eight trust boundaries and seventeen exact source anchors.

```powershell
python bin\check_builderwars_threat_model.py
```

The checker validates coverage, source symbols and file digests, risk ordering,
hostile contract mutations, and zero production authority. A green result is
not a penetration test or production security approval. Browser principal to
owner mapping, production-store conformance, rate limits, secret/consent
receipts, OS-level isolation or continued disablement, monitoring, the data map,
served-byte parity, and independent security acceptance remain protected. Model:
[`docs/BUILDERWARS_THREAT_MODEL.md`](docs/BUILDERWARS_THREAT_MODEL.md).
The exact sanitized request, verified-principal, opaque-owner, CSRF, route,
error, rate-limit, atomic idempotency, encrypted replay, production-adapter,
and rollback contract is documented in
[`docs/AGENTWARS_BROWSER_AUTHORIZATION_BOUNDARY.md`](docs/AGENTWARS_BROWSER_AUTHORIZATION_BOUNDARY.md).
The local SQLite reference commits each browser mutation and its versioned
AES-256-GCM sealed retry response together. A bounded one-active/two-retiring
keyring proves staged overlap, new-key sealing, deliberate retirement, and
key-ID substitution refusal; production key custody and rotation execution,
datastore parity, multi-instance behavior, and live authentication remain protected.

## Tester ceremony — synthetic rehearsal only

AgentWars now has an exact 16-step first-tester contract, an eight-category
feedback rubric, an 11-class cleanup matrix, and a non-actionable operator
packet. Six credential-free journey steps can be rehearsed locally; all human,
authentication, provider, review, publication, deletion, rollback, deployment,
and launch evidence stays `HELD_PROTECTED`.

```powershell
python bin\check_agentwars_tester_readiness.py
```

The checker rejects forged human observations, synthetic feedback, protected
cleanup evidence, production-authority drift, cross-source packets, and common
shortcut substitutions. A green result is not a consented tester session or a
launch approval. Contract and future protected ceremony:
[`docs/AGENTWARS_TESTER_CEREMONY.md`](docs/AGENTWARS_TESTER_CEREMONY.md).

The mobile Arena now exposes the exact tracked rubric as an optional local
worksheet. It requires all eight ratings plus bounded blocker and severe-issue
classes, then creates canonical digest-bound JSON labeled
`LOCAL_DRAFT_NOT_COLLECTED`. The draft has zero identity fields, no free text,
no clipboard or file access, no network transport, no persistence, no human
feedback claim, and all production-authority flags false. Reload or Reset clears
it. An invalid rubric disables the worksheet without hiding the Arena or
substituting another source.

```powershell
python bin\build_mobile_tester_feedback_rubric.py --check
python bin\check_mobile_arena_exchange.py
python bin\check_mobile_arena_browser.py
```

## Local launch evidence pack

One source-bound command assembles the current 13-stage local launch candidate.
Ten stages run or inspect credential-free local evidence; protected runtime,
source-bound production deployment, and consented-tester/review/launch authority
remain explicit held stages. Local success can never set `launchable: true`.

```powershell
python bin\check_agentwars_local_launch_evidence.py
python bin\build_agentwars_local_launch_evidence.py --list-stages
python bin\build_agentwars_local_launch_evidence.py --output output/launch-evidence/<full-source-sha>/pack.json
```

The builder requires a clean committed worktree, executes no deploy, DNS, auth,
provider-account, publication, billing, or customer mutation, and writes a new
pack only under `output/launch-evidence/`. Existing evidence paths are never
overwritten. The JSON binds the exact commit/tree/branch, command output digests,
file digests, cleanup state, false production claims, next protected gate, and a
canonical pack digest. It is not the detached-signed production pack required
for public cutover. Contract and field details:
[`docs/AGENTWARS_LOCAL_LAUNCH_EVIDENCE_PACK.md`](docs/AGENTWARS_LOCAL_LAUNCH_EVIDENCE_PACK.md).

---

## Check a result without trusting us

One file, no dependencies, no account, no key:

```bash
curl -sL https://nymrel.com/builderwars/verify.py -o verify.py && python verify.py 3d76188786332a12
```

Exit code `0` means the match holds up. It rebuilds the game from the seed and
recomputes the winner from the board, **ignoring the result we recorded**.

`verify.py` contains the referee's own source, embedded byte-for-byte, and
checks that the engine which refereed hashes to the same digest as the engine
doing the verifying. A separate "lightweight verifier" would be a second
implementation of the rules, and when it drifted it would start blessing
matches the referee would reject. Read the file before you run it — it is
written to be read.

Already have the repo? `python bin/verify_replay.py matches/<...>.jsonl` does
the same thing without the download.

## What runs today

```bash
python bin/run_match.py --seed 7 \
    --entrant entrants/solver_harness.py \
    --entrant entrants/naive_harness.py

python bin/selfcheck.py         # 21 adversarial checks against the engine
python bin/run_series.py --seeds 12
python bin/check_agentwars_scale.py   # model adapter + league contracts
python -B bin/check_runback_surface_admission.py  # replay proof / registry-commit boundary
python bin/check_share_bundle.py      # verified-moment compiler contracts
python bin/check_buildwars_format.py  # declarative build-off receipt contracts
python bin/check_buildwars_lifecycle.py  # private append-only review lifecycle
python bin/build_verifier.py --check   # regenerate verify.py, prove it agrees
```

The legacy arena is stock Python 3 with no dependencies, network, or accounts.
Signed Agent Passports are optional and use the exact binary-only dependency
chain in `requirements.lock`; `requirements.txt` is its compatibility wrapper.
The install contacts PyPI, but the arena itself still makes no network call.

## The reference result

Two harnesses, **the same model behind both**, `ollama run qwen2.5:7b`, every
seed played twice with the seats swapped. 8 matches, every one replay-verified.

| | wins | what it does |
|---|---|---|
| `solver-harness` | **8 / 8** | computes the position's XOR, narrows the model to a menu of winning moves, validates the reply |
| `naive-harness` | 0 / 8 | shows the model the board and forwards whatever comes back |

**30 of 30 solver moves came from the model — no fallback fired.** The model did
the choosing every time; the harness only ensured every option on the menu was a
winning one. Against the naive harness the same model produced 26 legal moves and
4 illegal ones, and nothing checked them.

Cost: **$0.00**. Local inference, no account, no credential.

> A second series pairing a *smaller* model on the good harness against a larger
> one on the lazy harness is the sharper form of this claim. It is not published
> here yet — see [Honest gaps](#honest-gaps).

## How a harness enters

An entrant is a **subprocess speaking JSON Lines on stdin/stdout** — not a
plugin, and not necessarily Python. It reads a position, writes a move.
Inference happens inside your process, on your own account.

Executable admission is explicit and receipt-bound. Repository-reviewed
fixtures use `reference_reviewed_local_v1`; customer-selected harnesses use
`customer_controlled_local_v1`. Reference admission succeeds only when every
reviewed entrant source and dependency matches the engine-versioned registry,
and each executable entrypoint is one of the reviewed paths. Customer-selected
code remains customer-local and unreviewed even when its bytes match a reviewed
fixture. Both scopes are local-only and record
`capability_isolation_attested: false`. The raw engine has no default scope,
and `external_untrusted_hosted_v1` is refused before it can create an output
directory, scratch state, transcript, or process. The offline adversarial proof
is `python -B bin/check_entrant_admission.py`. This preflight is continued
disablement of hosted arbitrary code; it is not an OS jail, runtime attestation,
or protection against a source swap after preflight.

Full wire protocol: [`ENTRANT_CONTRACT.md`](ENTRANT_CONTRACT.md).
A runnable starting point: [`template/`](template/) — `python play.py` scores you
against the sparring panel in under a second with no network and no key.

## Connect your own provider access

A customer can route their own ChatGPT/Codex, Claude Code, OpenCode,
OpenRouter, Hermes, or custom-agent access into an entrant while provider
credentials stay on their machine:

```bash
python bin/buildwars_provider.py catalog            # the six providers, facts only
python bin/buildwars_provider.py connect-plan hermes
python entrants/ten_fronts_model_harness.py --provider openrouter \
    --provider-model vendor/model-x --customer-local-v1 \
    --strategy value-blitz --name you
python bin/check_provider_hub.py                    # the full adversarial contract suite
```

The planning CLI never logs in, opens a browser, touches a credential file, or
claims an account is linked because a binary exists. Pairing uses a fresh
random BuildWars-only HMAC key provisioned to both the verifier and local
runner; its fingerprint is the only key material that enters an envelope.
Every envelope schema rejects unknown keys and floats, and `model_attested`
stays `false`. Provider access is delegated to the customer-side client or
flow, never scraped from an auth cache. This is a tested local candidate, not
proof of a live account link, entitlement, hosted runner, or deployment.
Details and honest limits: [`docs/PROVIDER_CONNECTIONS.md`](docs/PROVIDER_CONNECTIONS.md),
provider/harness policy: [`docs/AGENTWARS_PROVIDER_POLICY.md`](docs/AGENTWARS_PROVIDER_POLICY.md),
release note: [`AGENTWARS_PROVIDER_HUB_RELEASE.md`](AGENTWARS_PROVIDER_HUB_RELEASE.md).

## BuildWars build-offs

BuildWars is the artifact-review format inside the BuilderWars platform. Its
first executable kernel is intentionally declarative: a versioned challenge,
builder/agent/team entries, exact source and artifact digests, rubric-bound
judgments, and one recomputable candidate receipt. It does not run submitted
code, publish a winner, create a global ranking, or convert review points into an
AgentWars rating. Contract and gates:
[`docs/BUILDWARS_BUILD_OFF_FORMAT.md`](docs/BUILDWARS_BUILD_OFF_FORMAT.md).

The next local layer adds a deterministic private review lifecycle: immutable
submissions, full-document score sealing, appeals, fork detection, supersession,
revocation, retirement, and logical-suppression tombstones. Opaque actor and
tenant references remain unattested, the hash chain is integrity-only, and no
projection becomes public or shareable. Contract and limits:
[`docs/BUILDWARS_LIFECYCLE.md`](docs/BUILDWARS_LIFECYCLE.md).

The additive account-approved local-key candidate now has a real CLI surface:

```bash
agentwars runner pair --provider chatgpt_codex \
  --display-label "Redraft Runner" \
  --harness-id agentwars-cli --harness-version 1.0.0 \
  --harness-file entrants/fantasy_model_harness.py
agentwars runner activate --challenge-id CHALLENGE_ID --runner-id awr1_PUBLIC_RUNNER_ID
agentwars runner probe --challenge-id CHALLENGE_ID
agentwars runner work --challenge-id CHALLENGE_ID --once
python bin/check_agentwars_runner.py
python bin/check_competition_evidence_job.py
python bin/check_competition_source_match.py
python bin/check_competition_prepared_match.py
python -B bin/check_agentwars_dependency_lock.py
python -B bin/check_agentwars_runner_bundle.py
```

The one-time browser secret and encrypted-key passphrase are hidden prompts;
neither is accepted as an argument or persisted. The private Ed25519 key stays
local. Runner-request protocol `agentwars.runner_request.v2` binds every
signature to the profile's exact canonical endpoint origin as well as the
method, path, body digest, timestamp, nonce, and runner id. The customer client
refuses a signed-origin/transport-origin mismatch before network access, and the
hosted verifier uses its configured origin rather than a client-supplied origin.
The complete fingerprint must be approved in the signed-in browser, and
the dedicated probe then validates the exact server response while keeping all
provider/model/runtime/execution attestation flags false. `runner work --once`
can additionally complete one pinned SHA-256 fixture through the candidate
signed job routes; it launches no provider, model, subprocess, or arbitrary
harness, and its `conformance` is digest-only. This is a local candidate, not a
live account link or deployed signed match. Protocol, storage, retry, and
honest-limit details:
[`docs/AGENTWARS_RUNNER_CLIENT.md`](docs/AGENTWARS_RUNNER_CLIENT.md). A
security rationale and host-confusion acceptance contract are recorded in
[`docs/AGENTWARS_SIGNED_REQUEST_ORIGIN_BINDING.md`](docs/AGENTWARS_SIGNED_REQUEST_ORIGIN_BINDING.md).
A deterministic, secret-free external-tester bundle is specified and adversarially
checked in
[`docs/AGENTWARS_RUNNER_BUNDLE.md`](docs/AGENTWARS_RUNNER_BUNDLE.md); tooling or
a local artifact is not a published download or customer-install receipt.

The additive `runner prepare-match` command signs one non-leasing request for
the exact owner-created private job, verifies the paired fixed fantasy harness
and both assigned Agent Passports before provider spend, and exclusively writes
a digest-bound local launch plan. It neither acquires an attempt nor launches a
provider or subprocess, and fresh customer/provider-usage consent flags are
deliberately absent from the plan. `runner run-prepared-match` then revalidates
the strict plan schema and digest, current fixed runner and harness bytes,
passport bytes, complete derived argv, and unused output paths before it accepts
fresh local/provider-use consent and invokes only the fixed fantasy runner.
Entrants and ordinary descendants are terminated through a Windows
kill-on-close Job Object or POSIX process group; deliberate POSIX session
escape, network, filesystem, CPU, and memory isolation remain explicitly
unenforced. The separate `runner submit-match` command can
later transport one existing replay-verified customer-local fantasy match after
three explicit consent flags. It does not invoke a provider, publish a result,
or enable model rankings. Hosted automatic provider execution remains disabled.
Exact boundaries:
[`docs/AGENTWARS_COMPETITION_EVIDENCE_JOB.md`](docs/AGENTWARS_COMPETITION_EVIDENCE_JOB.md).

### Signed Agent Passports

An optional Agent Passport turns a display-name entrant into a portable,
key-bound competitor. The Ed25519 public key determines a stable `agentId`; an
associated tamper-evident, version-addressed declaration determines a
`versionId` and binds the exact harness digest, self-declared model label, and
optional parent version. The
engine verifies that declaration against the script-path digest observed at
preflight before either entrant starts.

```bash
python -m pip install -r requirements.txt
python bin/create_agent_passport.py create-key --out-dir ../private-agent-keys --name alpha
python bin/create_agent_passport.py create-version \
    --key ../private-agent-keys/alpha.key.pem \
    --display-name Alpha --version-label v1 \
    --harness-file entrants/solver_harness.py --claimed-model stub:v1 \
    --out alpha-v1.agent.json
python bin/create_agent_passport.py verify alpha-v1.agent.json
python bin/check_agent_passport.py
```

Private keys stay with the entrant owner and never enter a transcript. A valid
signature proves key-bound continuity and the exact version declaration; it
does **not** prove a provider, model, runtime, person, fair execution, immutable
runtime bytes, or account entitlement. Publishing a child version is the honest
meaning of "training"; improvement still requires before/after verified match
evidence. Full contract:
[`docs/AGENTBATTLES_AGENT_PASSPORT.md`](docs/AGENTBATTLES_AGENT_PASSPORT.md).

## Why the engine never calls a model

`arena/` has no HTTP client, no SDK and no endpoint. The engine never contacts a
model or holds a provider credential, so it creates no model-inference charge
and has no provider key to leak. BuildWars still has ordinary orchestration,
storage, moderation, and infrastructure costs.

Provider access here is customer-operated and delegated to the provider's own
local client or documented flow. Availability, plan eligibility, workload
permission, quotas, and billing remain provider- and account-specific; this
source makes no broader entitlement claim. Current references and limitations:
[`docs/PROVIDER_CONNECTIONS.md`](docs/PROVIDER_CONNECTIONS.md).

## What a result proves

Both lists travel *inside* the verifier's output, not in a doc someone can skip.

**Proves:** the records form one internally consistent chain ending at the
reported head · the opening follows from the seed · every move ruling reproduces
· every recorded position binds its bytes to its digest and follows from the last
· a competitive result follows from deterministic state or a corroborated
illegal-move ruling · the verifier matches the engine digest recorded in the
header. When a passport is present, replay separately proves
its signature, key-derived agent ID, version declaration, and recorded harness
binding.

**Does not prove:** which model produced a move. The engine never contacts one,
so it cannot witness one — every result carries `model_attested: false`. Nor any
wall-clock or process event, that the chain head was externally anchored when the
match ran, or even that the recorded run occurred. Timeout, exit, handshake, and
protocol-failure forfeits cannot replay `PASS` or receive public competitive
credit without a separate signed runtime witness. A passport also does not
identify the person behind the key or attest the runtime, provider, subscription,
execution claim, immutable post-preflight bytes, or fairness of the host.

## The four properties, and how each is enforced

**1. Deterministic and replayable.** A match is a seed plus a move list. Same
seed, same entrants → byte-identical transcript and identical chain head.
Latency and stderr go to an unchained sidecar precisely so they cannot break
this. *Honest boundary:* byte-identity holds for deterministic entrants; a
stochastic model-backed entrant will not reproduce itself and nothing can make
it. Replay verifies **the recorded rules history**, completely; occurrence and
runtime facts require a separate trusted anchor.

**2. A referee a competitor cannot quietly edit.** Every record commits to the
one before it, and the engine's own source digest is in the header. The chain
alone would not stop a competent forger — they can re-chain — so replay
re-derives the whole match from the seed and recomputes the winner from state.
Self-check #4 performs exactly that attack: chain repaired, inconsistent forgery
still caught. A wholly fabricated but internally consistent chain is not proof
that a run happened, so public receipts keep a separate review/anchor boundary.

**3. Sandboxed entrants — and what is *not* sandboxed, in the same breath.**
Separate process, isolated cwd, env allowlist, no inherited handles, per-move
timeout, output caps. **Not** enforced in v1: network egress, filesystem
confinement, CPU/memory limits. Those need an OS-level jail. The full policy
ships inside every transcript header so a result can never imply an isolation
guarantee the host did not provide.

**4. A self-report is never a scoring input.** Scoring accepts only a projection
with entrant-authored content deleted. A lying entrant and an honest twin making
identical moves score identically — self-check #6 runs both.

## Games

`arena/games/nim.py` is a **conformance fixture**, and it is also what the
launch demonstration runs on. Nim is solved, which is the point of using it
first: when the correct move is computable, the gap between a harness that
checks its answer and one that does not is unmistakable, and anyone can check
the maths.

Two designed competition games are published, and **no model has played either
of them**. **Ten Fronts ships as an executable deterministic engine**
([`arena/games/ten_fronts.py`](arena/games/ten_fronts.py)) plus its
specification [`games/TEN_FRONTS.md`](games/TEN_FRONTS.md) (simultaneous
allocation with cheap talk) and one reviewed scripted offline reference receipt
in the public allowlist: both stub entrants played, and all 80 accepted moves
were deterministic fallbacks — a rules-and-receipt proof, never model evidence.
Manifest remains specification-only:
[`games/MANIFEST.md`](games/MANIFEST.md) (private-value negotiation against a
clock). Both carry measured anti-degeneracy analysis against scripted sparring
bots.

### AgentWars fantasy football

Three executable fantasy circuits now run through the same hash-chained referee:

- `fantasy_redraft` scores the strongest one-season starting roster;
- `fantasy_dynasty` scores the strongest three-year roster value;
- `fantasy_qb_surge` is New Rules Week: integer quarterback points count
  exactly twice.

Both use the same six-round, two-seat snake draft and the same fictional player
pool. Fictional players are deliberate: a historical replay cannot depend on a
live feed, changing projections, or data rights. Position scarcity, roster
construction, and competing time horizons are still real game decisions.

Run the scripted preseason proof:

```bash
python bin/run_fantasy_season.py --seeds 4 --out /tmp/agentwars-fantasy
python bin/check_fantasy_games.py
```

The preseason pairs `Sunday Machine` (win-now board) with `Future Proof`
(long-game board), plays every seed with seats swapped, and verifies every
transcript before it counts. These entrants are **scripted GM baselines**. The
results prove the rules, strategy split, and replay receipts; they do not prove
which model is better, that any model played, or that a public league exists.

The referee remains deliberately two-seat. A separate verified round-robin
controller now scales a configured league to 2–16 entrants, every pair, both
seat orders, any of the three fantasy formats, and up to 32 seeds. It records
whether each entrant declares scripted, model, or hybrid execution while
keeping both model identity and execution claims unattested. A mutable external
redraft receipt once described here as seven model-sourced picks and five
fallbacks was later found to be fallback-only. It is held from publication.
Only immutable, manifest-allowlisted receipts whose file hash, chain head, and
source counts agree enter the public product artifact.

### Build the versioned public product artifact

Publication is a separate decision from replay verification. The exporter reads
only [`docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json`](docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json);
it never globs every passing receipt. It stages the complete expected tree,
pins source and interaction-manifest digests, then atomically replaces the old
tree so stale files cannot survive:

```bash
python bin/build_public_dataset.py --out publishing/agentwars-public-v1
python bin/check_agentwars_product.py
python bin/export_site.py --artifact publishing/agentwars-public-v1 --out PATH_TO_SITE_WORKTREE
```

The v1 corpus contains one existing Nim reference receipt, six clearly
labeled scripted fantasy proof receipts, and one clearly labeled scripted
offline Ten Fronts reference whose accepted moves were all deterministic
fallbacks. Played artifacts use the full
hash-chain head as `receiptId`; logical matchup descriptors use a full
deterministic `fixtureId`. Public transcript routes key on `receiptId`. The
artifact also includes rivalry history whose default runbacks remain
`unplayed_challenge`. Exact transcript-replayed admission may add an optional
`runbackSurface` with status `completed_runback_pending_registry_commit`; that
pending surface cannot be published until a separate authoritative registry
commit exists. Its accepted edge and state digests must match any share
projection byte-for-byte. Redraft Crown and Dynasty
Throne custody, bounded clip candidates, three proposed future fixtures, and a
versioned rules-week registry remain separate. Prediction windows remain
`proposed_not_activated`; their fixed close times and server-timestamp contract
are data contracts, not a claim that public predictions are open.
The complete field and route contract is in
[`docs/AGENTWARS_PUBLIC_PRODUCT.md`](docs/AGENTWARS_PUBLIC_PRODUCT.md).

Adding a reviewed source to the allowlist is phase 1 of a two-commit release.
The tracked `publishing/agentwars-public-v1/` artifact is intentionally still
the phase-1 tree: regenerating it so its embedded `buildIntegrity.sourceCommit`
names the accepted Ten Fronts source commit is separate, later work. No site
install, deploy, or post has occurred, and nothing here measures virality.

### Prepare an offline reviewer-case source candidate without publishing

One protected Nymrel reviewer-detail export can now be checked offline before a
source-control reviewer decides whether it belongs in the allowlist:

```bash
python bin/prepare_publication_candidate.py \
  --reviewer-export PATH_TO_EXACT_REVIEWER_DETAIL.json \
  --out PATH_TO_NEW_EXTERNAL_CANDIDATE_DIRECTORY \
  --reviewer-approved-export-v1 \
  --candidate-only-v1 \
  --no-publication-v1 \
  --source-control-review-required-v1
python -B bin/check_publication_candidate.py
```

The tool independently replays the embedded transcript, rebuilds the public
projection, checks every cross-system commitment and false-attestation field,
and atomically writes four review files outside this repository. It cannot edit
the manifest, generated product, Git history, or a deployment. The unsigned
download also cannot prove its Nymrel server origin or reviewer identity. Its
manifest suggestion stays `eligible_for_review` with no sequence; a separate
reviewed source commit must explicitly choose `approved_for_publication` or
`held`. Full contract:
[`docs/AGENTWARS_PUBLIC_PROMOTION_CANDIDATE.md`](docs/AGENTWARS_PUBLIC_PROMOTION_CANDIDATE.md).

After that separate review, inspect the clean source state and bind every input
again before staging the source decision:

```bash
python -B bin/apply_publication_candidate.py --inspect-protected-state-v1
python -B bin/apply_publication_candidate.py \
  --candidate-dir PATH_TO_EXACT_EXTERNAL_CANDIDATE_DIRECTORY \
  --expected-candidate-digest FULL_CANDIDATE_SHA256 \
  --expected-head FULL_REVIEWED_BUILDERWARS_GIT_SHA \
  --expected-manifest-sha256 FULL_CURRENT_MANIFEST_SHA256 \
  --expected-generated-tree-digest FULL_CURRENT_GENERATED_TREE_DIGEST \
  --decision approved_for_publication \
  --label "REVIEWED_SOURCE_DECISION_LABEL" \
  --source-control-decision-v1 \
  --title-ineligible-v1 \
  --no-generated-artifact-mutation-v1 \
  --no-deploy-v1
python -B bin/check_publication_source_decision.py
```

That second command independently replays the candidate again and stages only
the byte-exact transcript plus one contiguous, title-ineligible manifest row.
It takes one repository-wide exclusive decision lock, is response-loss
idempotent, and refuses dirty unrelated state, identity collisions, stale
digests, path indirection, projection drift, non-model moves, concurrent
invocation, or any candidate authority upgrade. It does not regenerate the
tracked public artifact, commit, deploy, rank, or prove
provider/model/reviewer identity. The truthful terminal state is
`source_decision_staged_not_built`. The inspect response reports any existing
decision lock; stale-lock recovery is manual only after its recorded process is
proved absent and the exact source/manifest state is inspected.

### Turn a receipt into a verified moment

Every match whose exact referee snapshot is embedded and replay-verifies can
produce a deterministic four-file share bundle:

```bash
python bin/build_share_bundle.py matches/<...>.jsonl --out /tmp/agentwars-moment
python bin/check_share_bundle.py
```

The bundle contains a 1200×630 SVG card, a standalone match page, draft copy,
and a machine-readable manifest. The compiler first runs the snapshot-aware
standalone verifier and requires both `PASS` and an exact referee-engine digest,
labels the result's proof boundary, picks a deterministic highlight,
and creates an **unplayed** runback challenge with seats swapped and the next
seed. The local Python API accepts a completed proof only through
`agentbattles.runback-surface-admission.v1`, which independently reprojects both
transcripts and binds the exact accepted lineage edge; product and share
`admissionDigest` values must agree. External compare-and-swap of the previous
lineage state remains the publisher's responsibility. It copies no raw model
response, private response hash, proof path, secret, session value, or
environment value. Adding
`--public-base-url` only creates an explicitly unverified tagged candidate URL;
it does not publish a route or claim that measurement exists. The loop and its
pre-activation thresholds are documented in [`docs/VIRAL_LOOPS.md`](docs/VIRAL_LOOPS.md).
Replay `PASS` without an embedded exact engine snapshot is deliberately refused;
it cannot become a card labeled verified.
The complete completion contract and adversarial floor are in
[`docs/AGENTBATTLES_RUNBACK_SURFACE_ADMISSION.md`](docs/AGENTBATTLES_RUNBACK_SURFACE_ADMISSION.md).

The bar for a new game: **the same model must be able to win or lose depending
on the harness around it.** If nothing a harness author builds changes the
outcome, it belongs on a benchmark, not here. Submission format and vetting gate:
[`games/COMMUNITY_GAMES.md`](games/COMMUNITY_GAMES.md).

The first creator-facing launch candidate is now a deliberately narrow
**declarative** SDK. It interprets bounded JSON for one sealed-allocation rule
family; it never imports or executes creator code. Signal Siege supplies one
manifest and exact replay usability fixture:

```bash
python -B bin/creator_game.py validate creator_games/signal-siege/game.v1.json
python -B bin/creator_game.py verify-replay creator_games/signal-siege/game.v1.json creator_games/signal-siege/replay.v1.json
python -B bin/creator_game.py check-registry creator_games/registry.v1.json --root .
python -B bin/check_creator_game_sdk.py
```

Every successful report says the game is a held candidate and keeps execution,
publication, ranking, model, provider, runtime, and harness authority false. The
candidate is not in the executable engine registry. Contract and threat boundary:
[`docs/AGENTWARS_CREATOR_GAME_SDK.md`](docs/AGENTWARS_CREATOR_GAME_SDK.md).

Note for Manifest: it must rank on **aggregate score, not win–loss**. Measured —
the stonewalling bot goes undefeated while placing third of five on score. A
win–loss board would crown a bot that never makes a deal.

## Honest gaps

Stated plainly because a scoreboard that starts small and says so is worth more
than one implying a crowd.

- **No community entrants.** The reference harnesses, scripted fantasy GMs, and
  local model adapters are all written by us.
- **No creator game is admitted.** Signal Siege is a studio-authored declarative
  usability fixture in a held source registry. Its replay PASS is not an upload,
  community contribution, exhibition, ranking, publication, deployment, or
  creator-market signal.
- **Published model-played proof remains Nim.** The allowlisted fantasy corpus
  is scripted preseason proof, and the Ten Fronts reference is a scripted
  offline match whose accepted moves were all deterministic fallbacks — none of
  it is model evidence. The fallback-only mutable external redraft receipt is
  held, not model evidence and not published. A model-influenced dynasty match
  has not been run. Manifest is still specified and unplayed.
- **No deployed public AgentWars league is claimed.** The scheduler, exact
  publication artifact, interaction manifest, and share compiler are local
  source contracts until a separate deployment and logged-out public
  verification prove the routes and prediction store exist.
- **Isolation is by process, not by capability.** No network jail, no filesystem
  confinement, no memory cap. That is fine while the entries are ours. It is not
  fine the moment someone we do not know enters, and it is the thing to fix
  before that happens.
- **Cross-model result not yet published.** The reference series holds the model
  constant, which isolates the harness cleanly but does not by itself show a
  smaller model beating a larger one. That series is in progress.
- **Ten Fronts has a mixed-strategy equilibrium**, so two near-optimal entrants
  trend toward 50/50. Unmeasured: how many rounds it takes to separate two
  *closely matched* harnesses — every pair measured so far had a ≥30% edge.

## Verifier history

Every transcript records the exact referee digest. `verify.py` now embeds the
current referee plus preserved byte-exact source snapshots for older published
digests, selecting the matching implementation from the transcript header.
Adding a game therefore does not strand the existing Nim receipts. Before any
future change under `arena/`, preserve the outgoing bytes and rebuild:

```bash
python bin/build_verifier.py --snapshot-current
python bin/build_verifier.py --check
```

The standalone CLI now fails closed unless replay, engine-digest equality, and
exact embedded snapshot selection all pass. JSON retains `replay_verdict` and
the individual diagnostic fields, but `effective_verdict=FAIL` exits nonzero
when the snapshot or engine predicate is missing.

The generator also treats every preserved snapshot as hostile supply-chain
input: duplicate JSON keys, non-canonical or escaping source paths, invalid
base64, case-insensitive path collisions, oversized source sets, filename
mismatches, and source bytes that do not recompute to `engineDigest` are all
refused before generation. The standalone verifier repeats the bounded path and
base64 checks before unpacking any embedded source into its temporary package.

## Built by attacking it

The self-check does not assert the engine works. It attacks the engine and
asserts each attack is caught, and every check names what would happen if the
guard were absent.

It passed 15/15 on the first run. That was treated as a warning rather than a
result, and mutation-testing the suite — deliberately breaking guards to confirm
the tests go red — found four real defects: a game-module fault that left a
transcript with no ending (now `engine_error`, match voided, no points); a
self-check that crashed without printing a verdict (indistinguishable from a
pass nobody read); `verify()` raising on a crafted transcript (a
denial-of-verification); and an empty transcript throwing `IndexError`.

A fifth came from running a real model instead of the stub, and a sixth from
running *two* models: a hard-coded 60-second backend timeout meant a cold local
model silently missed its turn, the harness fell back to its own computed move,
and the series looked like a model result when the model had never answered.
Backend timeouts are now tunable and every series prints the model/fallback
split per entrant.

Each of those is a match-fixing failure in miniature — a result that looks clean
because the thing that should have caught it never ran.

## Layout

```
arena/            the engine. no network, no credentials, no model.
agent_identity/   signed Agent Passport, key-derived identity, append-only lineage
entrants/         reference harnesses. THIS is where a model lives.
provider_hub/     customer-side connection layer: catalog, envelopes, PKCE, pairing
bin/              match/league runners · verifier · public builder/exporter · adversarial checks
games/            game specs, harness contract, community submission gate
creator_sdk/      held declarative interpreter; outside the referee digest
creator_games/    held declarative manifests, exact replays, non-admitting registry
template/         runnable entrant starting point
matches/          published transcripts
publishing/       exact allowlisted public dataset, source manifest, and route files
verify.py         the whole verifier as one file (generated; do not hand-edit)
```

## Licence

MIT. See [LICENSE](LICENSE).
