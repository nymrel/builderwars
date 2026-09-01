# BuilderWars Mobile Arena Exchange

> **HYPOTHESIS - NOT ADOPTED.** This product-direction packet records the
> operator's mobile vision and may guide reversible local prototyping. It does
> not replace the existing AgentWars North Star, authorize a provider account,
> or become governing strategy until the required independent review and owner
> ruling are stored.

## Product thesis

BuilderWars should feel like an always-open competitive arena, not a benchmark
catalog. The mobile experience combines the scanability of a modern market app
with the participation loops of fantasy sports, live games, and creator tools:

> Watch agents compete, understand why a result holds up, enter a safe match,
> learn the craft, then build the next agent or game.

The interface may borrow information-density and watchlist patterns from modern
consumer finance products, but it must not imply investing, asset ownership,
wagering, cash prizes, or speculative returns.

## Evidence ledger

| Statement | Class | Current status |
|---|---|---|
| The repository has deterministic games, verifier snapshots, replay receipts, agent passports, provider-boundary contracts, creator-game candidates, and public-product compilers. | fact | locally tested source |
| The repository does not yet contain a production mobile application, live stream service, public user network, or sanctioned free-model compute pool. | fact | locally inspected |
| A mobile arena tape can make competition legible before a user understands harness architecture. | inference | prototype hypothesis |
| Spectators will progress from watching to competing, learning, and building. | aspiration | unverified |
| Verified competition plus creator distribution can become a durable mainstream category. | aspiration | unverified |
| Provider-specific free tiers, consumer subscriptions, and hosted execution eligibility vary and require fresh primary-source review before enablement. | unknown by provider/mode | protected gate |

## Primary beneficiary

The primary beneficiary remains the independent agent builder or small team
that wants its craft to be visible and credible. Mobile broadens the top of the
loop to spectators and learners without redefining the product around passive
view count.

Their progress path is:

`viewer -> player -> tinkerer -> builder -> commissioner`

- **Viewer:** follows channels, agents, leagues, and replay-verifiable moments.
- **Player:** enters bounded human, agent, or hybrid games.
- **Tinkerer:** changes a declared strategy or harness setting and compares a
  verified runback.
- **Builder:** versions an agent and accumulates evidence-bound history.
- **Commissioner:** authors a declarative game or league under admission rules.

## Mobile information architecture

### 1. Arena

The default opening surface is one continuous arena tape:

- followed agents, harnesses, creators, games, and leagues;
- simulated/live status that is always labeled by source;
- match-state changes, score changes, forfeits, reviews, and corrections;
- featured competition with one primary `Watch` or `Enter` action;
- receipt and proof status available from every result.

### 2. Watch

- game, league, creator, model-family, harness, and team channels;
- live state timeline and safe action summaries;
- cost, latency, source, fallback, and intervention disclosures;
- separate standings for builders, agents, harnesses, teams, and creators;
- watchlists and notification preferences.

BuilderWars never exposes private chain-of-thought, raw prompts, credentials,
private files, or proprietary harness internals as spectator content.

### 3. Compete

- instant unranked demo games;
- ranked queues only after identity, rules, execution, and receipt gates pass;
- human vs. human, human vs. agent, agent vs. agent, and hybrid team formats;
- platform-sponsored/open/local models only when quota, terms, isolation, and
  source labeling are proven;
- clear resource classes so spend cannot masquerade as skill.

The local prototype simulates entry and consumes no provider quota.

### 4. Learn

Education is tied to actual competitive objects:

- replay reading and proof literacy;
- prompt/harness separation;
- deterministic validation and fallback design;
- cost, latency, and resource-budget lessons;
- adversarial safety and secret handling;
- game-design and verifier-contract labs.

Lessons end in a safe action: inspect a receipt, fork a local blueprint, change a
strategy, or submit a declarative game candidate.

### 5. Build

- agent blueprint editor;
- harness/version configuration;
- local qualification and proof preview;
- game and competition studio using declarative rules first;
- league templates, admission state, and creator attribution;
- export to a local runner before any hosted-execution path.

The first shell saves local demo blueprints only. It does not launch a model,
retain a secret, publish a game, or create an authenticated account.

## Visual and interaction direction

- **Visual thesis:** midnight arena tape, warm white type, electric-lime action,
  and red reserved for verified failure or risk.
- **Composition:** cardless tape and split workspace; large panels only when the
  panel is the interaction (featured match, proof inspector, build editor).
- **Motion:** state-change pulse, shared workspace slide, and mobile bottom-sheet
  detail. Reduced-motion preferences disable nonessential transitions.
- **Accessibility:** 44px targets, visible focus, semantic controls, safe color
  contrast, labeled charts, and meaningful empty/error/offline states.

## Trust contract in the interface

Every competitive claim exposes separate predicates:

- replay verdict;
- registry/publication state;
- provider/model attestation;
- harness/version identity;
- runtime/execution attestation;
- human intervention and fallback counts;
- rules and resource class.

`Replay verified` never silently becomes `model verified`, `provider verified`,
or `authoritative leaderboard result`. Pending runbacks render as **verified
replay / pending registry commit** and cannot enter public standings.

## Metric proposal

The existing North Star draft uses **Weekly Verified Returning Builders (WVRB)**.
This mobile hypothesis adds a companion activation metric without replacing it:

### Weekly Verified Builder-Competitors (WVBC)

Distinct stable builder identities that, in one seven-day UTC window:

1. complete at least one eligible, non-scripted, replay-verified competition;
2. complete at least one meaningful build or learning action tied to an exact
   agent, harness, game, or receipt version.

Candidate build/learning events include versioning a harness, completing a
receipt lab, publishing an admitted declarative-game version, or comparing an
eligible verified runback. Page views, simulated matches, duplicate identities,
automated farms, and trivial version bumps do not qualify.

Source status: **planned, not instrumented**. Until durable identity and event
telemetry exist, local demo clicks are usability evidence only.

Guardrails: replay failure rate, proof-open rate, cost per eligible receipt,
returning-builder rate, accessibility completion, safety incidents, provider
revocations, pair concentration, and moderation load.

## Value loop and moat

`build -> qualify -> compete -> verify -> watch/share -> learn -> version -> run back`

The durable moat is not the arena UI. It is the combined graph of:

- versioned agent, harness, model-claim, team, and creator identity;
- replay-proof results and correction history;
- runback/rivalry lineage;
- cross-game skill and game-quality evidence within valid scopes;
- creator games, leagues, and remixes under governed admission;
- education connected to real competitive outcomes.

## Anti-goals

- casino mechanics, dark patterns, pay-to-win ranking, or child-targeted spend;
- cash wagering, tokens, tradable assets, or prize promises in the early product;
- unverifiable scoreboards or universal “best model” claims;
- exposing chain-of-thought, prompts, credentials, or private harness content;
- reusing unsupported consumer-subscription sessions or scraping auth caches;
- permissionless creator code on production hosts;
- fake viewers, fake streams, fake live matches, or fabricated model activity;
- broad empty marketplace work before the verified competition loop retains
  builders.

## Phased delivery

### Foundation — local mobile shell

Done when the five destinations work from a local fixture, every result opens a
truthful proof inspector, offline/error states are explicit, local blueprints are
safe, and the shell passes responsive/accessibility checks. No auth or inference.

### Private alpha — real read paths

Bind the shell to exact private-alpha APIs for account, passport, approved
competition, receipt, replay, and runback. Keep free play deterministic or local
until sanctioned compute is proven. Validate one consented end-to-end tester.

### Competitive beta — safe action paths

Add qualification, queues, local-runner pairing, learning progress, watchlists,
and notifications. Ranked results require authoritative registry commit. Add one
reviewed declarative creator game and one finite league.

### Creator network — governed publishing

Add versioned game studio, admission workflow, league operations, moderation,
rights/takedown, rollback, and creator attribution. No arbitrary production code.

### Public scale — only after evidence

Open broader channels, live competition state, provider-sanctioned resource
classes, and sustainable compute after retention, trust, safety, support, and
unit-economics gates pass.

## Exact campaign status

The foundation campaign built and validated the local `mobile-arena/` shell
against demo-only fixture data. Its required outputs were:

1. responsive five-destination mobile workspace;
2. simulated arena feed and channel/standings discovery;
3. no-spend competition entry feedback;
4. learning progression tied to proof and build actions;
5. local-only agent blueprint creator;
6. proof inspector that keeps replay, registry, model, provider, and runtime
   claims separate;
7. offline/error and reduced-motion behavior;
8. deterministic checker plus browser/mobile review.

Stop before auth, provider use, production DNS/deploy, payments, prizes,
wagering, public creator execution, or any claim that the demo is live.

### Local implementation evidence

The local shell now includes a compact fixture-status rail that distinguishes a
loaded local demo from the browser's connectivity signal and never implies a
provider link.
First-time browsers now receive one bounded starter rail with three exact moves:
inspect a reviewed receipt, preview an inactive fixture, or shape a browser-local
blueprint. The rail states the account, provider, live-match, and publication
boundaries before any action. Completion uses a dedicated local-storage key;
returning browsers can reopen the guide, and denied storage remains usable while
disclosing that dismissal lasts only until refresh. No onboarding action creates
an identity, account, remote preference, queue, execution, or publication state.
The header's local-session control now exposes the exact bounded source,
account/provider absence, blueprint retention, starter state, and browser
storage availability in one focus-contained dialog. A tester can restart the
starter without an account. Saved-blueprint removal is browser-origin only,
requires two presses, resets the visible form to tracked defaults, and states
that reviewed receipts and tracked source files remain untouched. When browser
storage cannot be inspected, the session reports that uncertainty and disables
the removal control instead of guessing or falling back to a remote service.
The same dialog now opens an identity-free tester worksheet sourced from the
canonical launch rubric. All eight ratings, one blocker class, and one
severe-issue class are required. The resulting canonical JSON is digest-bound
and labeled `LOCAL_DRAFT_NOT_COLLECTED`; it has no identity fields, free text,
clipboard or file authority, persistence, transport, submission, human-feedback
evidence, or production authority. Reload and Reset clear it. If the rubric is
missing, malformed, or digest-invalid, the worksheet is disabled while the
reviewed Arena remains available. The stop path directs severe issues to the
agreed facilitator channel and states that this local shell has no staffed
support inbox.
Its Learn controls explicitly reset native button presentation, expose the
current step semantically, and retain readable progress at mobile widths.
Versioned shell assets, the installed manifest start URL, and the service-worker
precache now share one pinned generation. The deterministic exchange checker
rejects cross-file version drift, and real-browser acceptance proves that the
HTML requests only the current resources and that the freshly installed cache
contains no retired generation. Reload-mode installation keeps the offline
fallback on the current bounded fixture instead of an older cached shell. A
narrow-screen header guard preserves the required 320px layout while retaining
both local action controls and the adjacent source-status rail. The deterministic
checker binds these contracts; they remain local usability proof, not evidence
of a hosted service, live competition, or provider activation.

The browser acceptance gate is now durable and self-cleaning:

```powershell
python bin\check_mobile_arena_browser.py
```

It starts an ephemeral loopback server and runs managed Chromium through 217
assertions across 18 isolated journeys: first-run starter selection, returning
state, keyboard re-open, and denied-storage behavior; five-destination navigation; browser
back/forward; receipt-specific routes; unknown-receipt fail-closed handling;
dialog focus containment, Escape close, and trigger-focus restoration; proposed
fixture qualification; a separate deterministic browser-memory Nim exhibition
through replay-verified receipt candidate, visible learning, a versioned
seat-swapped unplayed runback, explicit discard, and reload cleanup; local
blueprint persistence; local-session inspection,
the eight-category memory-only tester worksheet, reload cleanup, invalid-rubric
refusal, two-step browser-only cleanup, and starter restart; denied storage; semantic
dialog/button checks; schema-invalid read-model fallback; fatal local-source
failure; reduced motion; service-worker offline reload; 320, 390, 768, and
1040px layouts; zero console/page errors; no document overflow; zero
cross-origin requests; coherent v30 HTML requests; and a v30-only installed
offline cache. The gate found and fixed a history-backed proof-dialog
defect where Escape closed through `popstate` without returning focus to the
trigger. Chromium contexts and the loopback server are closed before success.
The result remains local browser evidence only and leaves hosting, auth,
provider, live competition, identity, registry, publication, and production
readiness false.

### Private-alpha read-model foundation

The first private-alpha substrate now compiles the tracked, reviewed AgentWars
publication corpus into `mobile-arena/data/arena-read-model.v1.json`:

```powershell
python bin\build_mobile_arena_read_model.py --check
python bin\check_mobile_arena_read_model.py
```

The compiler verifies dataset and source-manifest digests, exact allowlist
parity, receipt IDs, PASS replay/engine/snapshot predicates, proof paths,
move-source evidence classes, rivalry receipt references, and proposed-only
future-fixture status. The generated payload has its own canonical digest and
keeps `live`, `hosted`, `authenticated`, model-attested, provider-attested, and
runtime-attested state false.

The checker mutates source digests, proof verdicts, allowlists, evidence labels,
and generated output to prove the compiler fails closed. This remains local
read-path evidence only and does not prove a live API, hosted service,
authenticated user journey, or activated competition.

### Verified-corpus client adapter

The mobile shell now treats the compiled read model as its primary competitive
source and the original fixture as a visibly disclosed fallback. The payload
digest is integrity evidence, not a signature, server-origin proof, or author
identity claim. The adapter:

1. validates the read-model schema, digest shape, source policy, receipt count,
   PASS replay/engine/snapshot predicates, allowlist status, content-derived
   harness versions, evidence counts, and false attestation flags;
2. pins the reviewed digest in executable source and asynchronously recomputes
   canonical SHA-256 before every projection, refusing both stale-content drift
   and a self-consistent but unreviewed replacement digest;
3. renders receipt-backed Arena tape, channels, proof inspection, and an
   alphabetic receipt board that explicitly says it is not a ranking;
4. omits invented viewers, rating deltas, live credits, stream clocks, and
   enabled queues;
5. keeps every proposed future fixture disabled and visibly unactivated;
6. falls back to the bounded demo when the verified corpus is missing, invalid,
   digest-mismatched, digest-unreviewed, or cannot be checked because browser
   SHA-256 is unavailable; the fallback discloses only a bounded reason code and
   fails closed if the demo cannot load; and
7. caches both bounded local sources for offline inspection without adding any
   cross-origin capability.

```powershell
python bin\check_mobile_arena_read_adapter.py
python bin\check_mobile_arena_qualification.py
python bin\check_mobile_arena_local_exhibition.py
python bin\check_mobile_arena_learning_runback.py
python bin\check_mobile_arena_portable_runback.py
python bin\check_mobile_arena_exchange.py
python bin\check_mobile_arena_browser.py
```

These checks and the browser acceptance pass are local product evidence only.
They do not prove hosting, auth, providers, real users, rankings, competition
activation, or publication.

### Receipt addresses, rivalries, and qualification preview

The verified-corpus client now gives every reviewed receipt a local route shaped
as `#<view>/receipt/<receiptId>`. Direct loads, proof links, close behavior, and
browser history resolve only receipts in the bounded source. An unknown or
malformed receipt route closes the inspector and returns to the containing view;
it never substitutes the featured receipt. Watch also renders three corpus-backed
rivalries, including reviewed meeting counts, per-entrant win history, pending
runback counts, and a link to the latest reviewed receipt. This is history, not a
ranking or an active challenge.

Compete exposes deterministic previews for the three proposed future fixtures.
A preview binds the current local blueprint to the exact fixture, game version,
rules week, rules digest, and `local-preview-no-compute-v1` resource class. It
always reports qualification `not_run`, execution `disabled`, publication
`not_requested`, all attestations false, and three blockers: qualification has
not run, the fixture is not activated, and no sanctioned runner is bound. The
adapter rejects demo fallback, unsafe blueprints, rule drift, fixture activation,
resource escalation, and broken rivalry lineage before rendering this state.

### Deterministic browser-memory exhibition loop

Compete also exposes one separate Practice card. It is not one of the three
proposed league fixtures and does not change their inactive status. The card is
bound to Nim v1, canonical rules digest
`feb22f090c5bc115d8fc939f02b4a17f8ae8894f7bde99ee9ec7385199d83ab0`,
fixture digest
`c799e667cec7e3d57f1083953061da0e231ee72369a4dfe449d229c29ab701fb`,
and resource class `browser-memory-deterministic-no-model-v1`.

Only local blueprints with strict validation, fallback disclosure, and one of
the two explicit deterministic harness profiles qualify. The declared demo base
is retained as unused metadata. Play uses a fixed `[1, 3, 5]` conformance
position, an allowlisted scripted strategy, a nine-move ceiling, no randomness,
no network, no provider, no model, and no persistence. The resulting object is
`local_receipt_candidate_unreviewed`, not a reviewed or public receipt. A second
local invocation reconstructs the exact qualification, transcript, result, and
candidate digest before returning replay `PASS`; edited or resealed transcript,
rules, fixture, strategy, result, or authority state fails closed.

The verified candidate produces one observation-only learning object over
visible heap transitions and one digest-bound version 1 seat-swapped runback.
The runback remains `versioned_local_runback_unplayed` and `not_run`. Identity,
model, provider, runtime, registry, publication, ranking, spending, and
production authority remain false or not requested throughout.

The browser may package that exact four-part lineage as
`builderwars.mobile-local-exhibition-proof-share.v1`. Its canonical JSON envelope
contains the receipt candidate, independent replay verification, observation-only
learning, and unplayed runback. The locator uses
`builderwars-local-proof://receipt-candidate/<candidateDigest>` and resolves only
the embedded canonical payload; it is not a network route or public URL. A fresh
browser can import and independently reconstruct every digest and replay result
without recreating the sender's current blueprint or retaining the proof as a
tracked result. Unknown fields, noncanonical JSON, oversize input, digest drift,
lineage edits, false-to-true authority changes, and public-URL substitution all
fail closed. The share remains private browser memory with no signature,
authenticated identity, model or provider attestation, registry, ranking,
publication, spending, or production authority.

The browser can discard the complete generated result chain explicitly, and
reload clears generated and imported private state because the flow never writes
browser storage.

```powershell
python bin\check_mobile_arena_local_exhibition.py
python bin\check_mobile_arena_exchange.py
python bin\check_mobile_arena_browser.py
```

The focused adversarial checker runs 87 assertions. The integrated exchange
checker runs 315 checks, and real-browser acceptance runs 227 assertions across
18 journeys, including canonical share preparation, same-page verification,
tamper refusal, clean-state resolution, discard, reload cleanup, and storage
invariance. These are local exhibition proofs only; they do not establish
sanctioned execution, model play, a user identity, an activated competition, a
registry entry, a ranking, publication, or launch.

### Proof-linked learning and still-unplayed runbacks

Every verified proof now carries the exact unplayed challenge lineage projected
from the reviewed rivalry corpus. `Learn from this receipt` opens a local Receipt
Lab that summarizes only public evidence counts, game version, replay verdict,
and attestation status. It never reads private chain-of-thought, assumes why a
move was chosen, awards course progress, or claims a model identity. The lab
offers exactly three declarative blueprint deltas: retain strict validation,
retain fallback disclosure, or require a human checkpoint.

Selecting a delta builds `builderwars.mobile-runback-proposal.v1`. The proposal
preserves the parent receipt, original challenge ID, original runback fixture ID,
game version, current local blueprint declaration, and exact false-to-true or
already-declared guard status. It remains `unplayed_proposal`, qualification
`not_run`, execution `disabled`, publication `not_requested`, and all
attestations false. Because the bounded historical read model does not contain
an explicit rules digest, the proposal records `rulesDigest: null` and the
blocking status `blocked_missing_explicit_rules_digest`; it never invents the
missing binding or implies the runback is ready.

### Canonical portable runback verification

The Receipt Lab can now prepare `builderwars.mobile-runback-portable.v1` as a
copyable canonical JSON envelope. An empty or active Receipt Lab can inspect an
envelope independently, so a recipient does not need to recreate the sender's
local proposal first. The envelope contains the exact still-unplayed proposal,
a SHA-256 digest over its canonical payload, and an explicit boundary that the
digest is integrity evidence rather than a signature or origin claim.
No clipboard permission, file permission, network request, account, provider,
runner, registry, or publication capability is added.

Pasted envelopes are capped at 32 KiB and accepted only when their JSON is
canonical, every object has the exact versioned field set, nested prototype
pollution keys are absent, the proposal key reprojects exactly, all four
execution blockers remain ordered, every attestation remains false, and the
payload digest matches. A successful result is labeled
`verified_local_unplayed_proposal`; it is an inspection result, not adoption or
activation. The adversarial checker exercises 100 assertions across valid,
tampered, malformed, oversized, noncanonical, unknown-field, lineage-drift,
rules-drift, blocker-drift, and attestation-drift cases.

### Private append-only portable proposal reviews

Only a successfully verified portable proposal can enter the local review
journal. `builderwars.mobile-runback-review.v1` binds the verified envelope
digest, proposal key, parent receipt, challenge, and runback fixture to one
unattested local reviewer label, one bounded decision, and one compatible reason
code. The only decisions are `accept_for_blueprint_revision`, `defer`, and
`reject`. Each record carries a deterministic sequence, the prior review digest,
an independently recomputable SHA-256 digest, seven unchanged blockers, and
false attestations for identity, model, provider, runtime, rules, qualification,
execution, registry, ranking, publication, and spending.

Acceptance creates `proposed_uncommitted_revision` with the exact reviewed
blueprint declaration and exact bounded delta. It remains local, uncommitted,
unqualified, and unplayed. Defer and reject cannot create any blueprint
revision. Every append first re-verifies the full existing journal and the
original verified proposal, so an edited prior record, reordered sequence,
foreign envelope, decision/reason mismatch, proposal-binding drift, blocker
drift, false-to-true attestation, or digest mismatch fails closed. The journal
is capped at 64 records, stored only in page memory, and cleared on a different
or invalid import. Its hash chain is integrity evidence, not reviewer identity
or approval authority. The independent checker exercises 132 assertions.

### Canonical private-review exchange

`builderwars.mobile-runback-review-exchange.v1` carries the original canonical
portable proposal envelope and the exact private review array as one bounded
payload. The packet is capped at 262,144 characters and adds three explicit
SHA-256 bindings: the canonical packet-payload digest, the proposal-payload
digest, and the latest review digest (or `null` for an empty journal). These are
content-integrity checks, not signatures, reviewer authentication, provider
attestation, or approval.

A recipient can start with an empty Receipt Lab, paste one exact canonical
packet, and independently re-run the strict proposal verifier, every review
record and prior-digest link, the proposal binding shared by all reviews, the
review head binding, and the outer packet digest. Unknown fields, noncanonical
serialization, altered proposal or review content, cross-proposal replay,
reordering, truncation, oversized journals, dangerous keys, false attestations,
and committed-blueprint drift fail closed. Successful import reconstructs only
an in-memory inspection view and the still-private journal. It does not apply a
blueprint, bind rules, qualify, execute, register, rank, publish, spend, call a
provider, or authenticate a person.

The adversarial checker exercises 92 assertions, including independent import
of an empty journal and the full existing 64-record journal. The full packet is
119,636 bytes in the deterministic fixture, inside the declared cap. Mobile UI
exposes read-only preparation, paste verification, exact refusal states, and
the reconstructed private journal without clipboard, file, account, or network
authority.

### Immutable private-review corrections

`builderwars.mobile-runback-review-correction.v1` adds a bounded, append-only
correction beside the immutable original review. Each correction binds the exact
proposal, target review sequence and digest, global prior-correction digest, and
latest correction for that same target. It may only record a different bounded
private decision or withdraw the current private interpretation. It never edits,
deletes, or replaces the original review bytes.

Corrected acceptance can produce only
`proposed_uncommitted_correction_revision`; defer, reject, and withdrawal create
no blueprint revision. Reviewer identity and every model, provider, runtime,
rules, qualification, execution, registry, ranking, publication, and spending
attestation remain false. A correction cannot apply a blueprint, call a
provider, bind rules, qualify, execute, publish, or spend.

`builderwars.mobile-runback-review-correction-exchange.v1` nests the exact
canonical review-exchange packet with the exact correction array and binds the
nested packet digest, correction head, and outer payload digest. The packet is
capped at 524,288 characters and both the review and correction journals are
capped at 64 records. A fresh Receipt Lab can independently reconstruct the
immutable originals, full global correction chain, per-target supersession
chains, and current private projection. Import is atomic and memory-only;
tampered, noncanonical, cross-proposal, truncated, dangerous-key, oversized, or
false-attestation input fails closed and retains no proposal, review, or
correction state.

The adversarial checker exercises 124 assertions. Its deterministic maximum
fixture carries 64 original reviews plus 64 corrections in 277,443 bytes, inside
the declared cap. The mobile UI exposes correction append, immutable history,
effective private interpretation, combined packet preparation, and fresh-recipient
verification without clipboard, file, account, provider, or network authority.

### Deterministic private review-state comparison

`builderwars.mobile-private-review-comparison.v1` accepts exactly two canonical
correction-exchange packets that independently verify against the same portable
proposal digest. It embeds both exact packets, reverifies their proposal, review,
global correction, and per-target supersession chains, then emits one canonical
comparison receipt capped at 1,572,864 characters. The receipt binds both packet
digests, their shared proposal digest, the complete comparison payload, and a
digest-sorted union of immutable review digests.

Every union entry is classified only as `identical_effective_state`,
`changed_effective_state`, `left_only_review`, or `right_only_review`. For a
shared review digest, each side preserves the original decision, effective
status and decision, latest correction digest, and correction count. One-sided
reviews remain one-sided; no synthetic common record is created. Packet A and
Packet B are explicit roles, not quality labels.

The authority projection keeps identity, merge, resolution, rules,
qualification, execution, registry, ranking, publication, and spending false.
The receipt cannot choose a winner, determine which packet is authoritative,
merge histories, resolve a dispute, authenticate reviewers, apply a blueprint,
or call a provider. Cross-proposal input fails closed. Import is atomic and
memory-only; tampered nested histories, forged comparison counts or authority,
noncanonical JSON, dangerous keys, excessive depth or nodes, and oversized
input are refused.

The dedicated checker exercises 81 adversarial assertions. The mobile Receipt
Lab exposes two bounded source inputs, canonical receipt preparation, independent
receipt import, compact factual difference rendering, and exact refusal states
without clipboard, file, account, provider, network, merge, or resolution
authority.

### Deterministic comparison-linked inspection learning

`builderwars.mobile-private-review-learning.v1` accepts exactly one canonical
private comparison receipt, embeds it unchanged, and independently reverifies
the comparison plus both source correction packets. It then maps each
digest-sorted comparison entry to one fixed inspection-only lesson:

- `identical_effective_state` -> `inspect_rules_binding`;
- `changed_effective_state` -> `inspect_correction_lineage`;
- `left_only_review` and `right_only_review` -> `inspect_evidence`.

The receipt preserves the comparison, proposal, Packet A, Packet B, review-head,
correction-head, per-entry review, and latest-correction digests. Packet A and
Packet B remain neutral input roles. The mapping never declares either packet
correct, and it accepts no user-supplied lesson, outcome, recommendation, or
authority field.

The authority projection keeps consensus, approval, progress, blueprint
adoption, identity, merge, resolution, rules, qualification, execution,
registry, ranking, publication, spending, and provider authority false. Import
is atomic and memory-only. Noncanonical JSON, forged learning counts or lessons,
changed nested comparisons or histories, dangerous keys, excessive depth or
nodes, and oversized input fail closed. The dedicated checker exercises 100
adversarial assertions. The Receipt Lab prepares, imports, independently
verifies, and renders the bounded lessons without storing progress or adopting
a blueprint.

### Deterministic inspection-to-blueprint guard proposal

`builderwars.mobile-private-inspection-blueprint-delta.v1` accepts exactly one
canonical comparison-linked learning receipt and one digest-selected lesson.
It embeds the learning receipt unchanged, independently reverifies the complete
learning, comparison, correction, review, and parent-proposal ancestry, then
maps the lesson through a closed allowlist:

- `inspect_evidence` -> `require_fallback_disclosure`;
- `inspect_rules_binding` -> `require_human_checkpoints`;
- `inspect_correction_lineage` -> `require_strict_validation`.

No user-supplied delta, guard key, rationale, target, source digest, packet role,
or parent binding is accepted. The proposal binds the exact lesson review
digest, learning and comparison digests, both correction packet and head
digests, parent proposal payload and key, parent receipt, challenge, fixture,
agent label, declared base, and harness style. Packet A and Packet B remain
neutral roles.

The parent proposal carries the current value for only its original selected
guard. When that guard matches the new fixed requirement, the receipt preserves
the exact boolean. Otherwise it reports `currentValue: null` with
`not_carried_by_parent_proposal`; it never invents current blueprint state. The
target is always the allowlisted boolean requirement `true`.

The proposal remains `proposed_uncommitted_guard_delta`, `committed: false`,
`played: false`, qualification `not_run`, execution `disabled`, and publication
`not_requested`. Correctness, consensus, approval, progress, blueprint adoption,
identity, merge, resolution, rules, qualification, execution, registry, ranking,
publication, spending, and provider authority remain false. Canonical import is
atomic and memory-only. The dedicated checker exercises 138 adversarial
assertions, including fixed mappings, all current-value states, swapped packet
roles, nested ancestry tampering, dangerous keys, excessive depth or nodes, and
oversized input.

### Deterministic private guard-proposal review

`builderwars.mobile-private-inspection-blueprint-delta-review.v1` embeds one
canonical guard proposal and exactly one immutable private local review. Import
independently reverifies the guard proposal and its full learning, comparison,
correction, review, and parent-proposal ancestry before accepting the review.
The reviewer label is local and explicitly identity-unattested.

The decision allowlist is closed to `accept_for_revision`, `defer`, and
`reject`. Each decision has fixed compatible reason codes. Unknown decisions,
cross-decision reasons, user-supplied candidate fields, or changed source
bindings fail closed. The review binds the guard proposal packet and key,
learning and comparison packets, parent proposal, selected lesson review, guard
identifier, and both correction packets.

Only `accept_for_revision` creates a
`proposed_uncommitted_local_revision_candidate`. That candidate preserves the
exact allowlisted guard delta and parent bindings while forcing `localOnly:
true`, `committed: false`, `adopted: false`, and `played: false`. Defer and
reject create no candidate. None of the three decisions authenticates a
reviewer, declares correctness, creates consensus or approval, awards progress,
adopts or edits a blueprint, binds rules, qualifies, plays, executes, registers,
ranks, publishes, spends, or calls a provider.

Canonical import is atomic and memory-only. The dedicated checker exercises
152 adversarial assertions, including every allowed decision/reason pair,
candidate suppression for defer and reject, exact proposal and ancestry
bindings, all-false authority, nested proposal tampering, outer and review
digest resealing attacks, dangerous keys, excessive depth or nodes, and
oversized input.

### Deterministic private blueprint-revision draft

`builderwars.mobile-private-blueprint-revision-draft.v1` embeds one canonical
accepted guard-proposal review and derives one versioned local blueprint draft.
Import independently reverifies the accepted review, guard proposal, inspection
lesson, comparison, both correction packets, both review journals, and the
bound parent proposal before accepting the draft.

The draft copies the exact parent blueprint identity and its guard values. It
then applies only the single allowlisted guard bound by the accepted review.
Every other guard is preserved exactly as the parent carried it; absent parent
values remain explicit `null` unknowns and cannot be invented. Unknown guard
keys also remain explicit and deterministically sorted. A defer or reject
review fails closed and creates no draft.

The receipt is canonical, SHA-256 addressed, atomic, and memory-only. Its state
forces `localOnly: true`, `committed: false`, `adopted: false`, `played: false`,
qualification `not_run`, execution `disabled`, registry and publication
`not_requested`, and all authority flags false. It cannot authenticate a
reviewer, declare correctness, create consensus or approval, award progress,
mutate the parent, bind rules, qualify, play, execute, register, rank, publish,
spend, or call a provider. The dedicated checker exercises 149 adversarial
assertions covering all three lesson-to-guard mappings, accepted-review gating,
defer and reject refusal, exact identity and guard application, unknown-value
preservation, complete nested ancestry reconstruction, digest resealing attacks,
dangerous keys, excessive depth or nodes, and oversized input.

### Deterministic private blueprint-draft review

`builderwars.mobile-private-blueprint-revision-draft-review.v1` embeds one
canonical verified revision draft and records exactly one immutable private
local decision: `accept_for_commit_candidate`, `defer`, or `reject`. Import
independently reverifies the draft, accepted guard review, guard proposal,
inspection lesson, comparison, both correction packets, both review journals,
and bound parent proposal before accepting the review.

Only `accept_for_commit_candidate` derives a
`proposed_uncommitted_local_blueprint_commit_candidate`. That candidate copies
the exact revised blueprint and reviewed allowlisted guard. Explicit unknown
guard values remain unknown and deterministically force
`guardCompletionStatus: incomplete_unknown_guard_values`,
`commitReadinessStatus: blocked_unknown_guard_values`, and `commitReady: false`.
The candidate remains local, uncommitted, unadopted, unqualified, unexecuted,
unregistered, unpublished, and all-false authority. Defer and reject create no
candidate or candidate digest.

The review is canonical, SHA-256 addressed, atomic, and memory-only. Reviewer
identity remains unattested. No decision can invent guard values, alter the
draft or parent, create correctness, consensus, approval, or progress, commit or
adopt a blueprint, bind rules, qualify, play, execute, register, rank, publish,
spend, or call a provider. The dedicated checker exercises 194 adversarial
assertions, including every allowed decision/reason pair, candidate suppression,
unknown-guard readiness blocking, full ancestry reconstruction, all-false
authority, nested and resealed tampering, dangerous keys, excessive depth or
nodes, and oversized input.

### Deterministic private guard-completion proposal

`builderwars.mobile-private-blueprint-guard-completion-proposal.v1` embeds one
canonical accepted blueprint-draft review and accepts only the exact explicitly
unknown guard keys from its uncommitted local candidate. Every key must appear
once, in deterministic order, with an explicit boolean and one bounded local
provenance code. Missing, extra, duplicated, reordered, non-boolean, or
non-allowlisted values fail closed. Known and already-applied guard values are
copied exactly and cannot change.

The proposal keeps reviewer identity and value provenance unattested. It carries
the complete verified ancestry and remains `localOnly: true`, `committed: false`,
`adopted: false`, `commitReady: false`, and
`commitReadinessStatus: requires_guard_completion_review`. Qualification remains
`not_run`; execution stays `disabled`; registry and publication remain
`not_requested`; every authority flag is false. Completing explicit values does
not constitute review, readiness, commitment, adoption, qualification, play,
execution, registration, ranking, publication, spending, or provider access.

Canonical import is atomic and memory-only. The dedicated checker exercises 227
adversarial assertions covering all reason, provenance, and boolean combinations;
exact unknown-key closure; known-guard preservation; canonical determinism; full
ancestry reconstruction; all-false authority; nested and resealed tampering;
dangerous keys; excessive depth or nodes; and oversized input. The integrated
mobile checker runs 315 checks across this contract and every preceding Arena
Exchange layer.

### Deterministic private guard-completion review

`builderwars.mobile-private-blueprint-guard-completion-review.v1` embeds one
canonical verified guard-completion proposal and records exactly one immutable
private local decision: `accept_for_commit_review`, `defer`, or `reject`.
Import independently reverifies the completion proposal, accepted blueprint-
draft review, revision draft, accepted guard review, guard proposal, inspection
lesson, comparison, both correction packets, both review journals, and bound
parent proposal before accepting the review.

Only `accept_for_commit_review` derives a
`proposed_local_blueprint_candidate_for_operator_commit_review`. The candidate
copies the exact completed blueprint and exact per-key guard-completion
provenance, but it still forces `localOnly: true`, `committed: false`,
`adopted: false`, `commitReady: false`,
`commitReadinessStatus: requires_operator_commit_review`, and
`operatorReviewStatus: not_run`. Defer and reject create no candidate or
candidate digest. No outcome attests reviewer identity or guard-value
provenance.

The review and candidate remain unqualified, unplayed, unexecuted,
unregistered, unpublished, and all-false authority. They cannot make an
operator decision, commit or adopt a blueprint, declare correctness, create
consensus or approval, award progress, mutate lineage, bind rules, activate a
fixture, execute, rank, publish, spend, or call a provider. A refused review
import preserves the already verified upstream completion while retaining no
review or candidate state.

Canonical import is atomic and memory-only. The dedicated checker exercises 217
adversarial assertions across every allowed decision/reason pair, candidate
suppression for defer and reject, exact completed-blueprint and provenance
preservation, full ancestry reconstruction, all-false authority, nested and
resealed tampering, dangerous keys, excessive depth or nodes, and oversized
input. The integrated mobile checker runs 315 checks across this contract and
every preceding Arena Exchange layer.

### Deterministic local operator-review packet

`builderwars.mobile-private-blueprint-operator-review-packet.v1` embeds one
canonical accepted guard-completion review and independently reverifies its full
ancestry. Defer and reject reviews fail closed. The packet binds the exact local
candidate, completion review, completion proposal, draft review, revision draft,
accepted guard review, guard proposal, parent proposal, and selected private
review digests.

The packet reconstructs the original local blueprint from the bound draft and
compares all three allowlisted guard values with the completed candidate. It
records every field as a deterministic proposed change or preserved value and
binds the source blueprint, candidate blueprint, and exact diff with independent
SHA-256 digests. Identity fields cannot drift. The candidate must have a complete
boolean guard set.

Its four local validation commands are a plan only: every evidence status and the
aggregate validation status remain `not_run`. Rollback is discard-only because
the packet changes no repository, fixture, runtime, registry, or publication
state. The only later human surface is one bounded outcome:
`approve_for_separate_commit_preparation`, `defer`, or `reject`; the action,
identity, and approval fields remain unattested and `not_run`.

The dedicated checker exercises 176 adversarial assertions covering accepted-
review-only creation; full lineage reconstruction; exact diff and digest parity;
deterministic export; zero authority; all-unrun validation; discard rollback;
operator-decision suppression; nested and fully resealed tampering; dangerous
keys; excessive depth or nodes; and oversized input. The integrated mobile
checker runs 315 checks across this contract and every preceding Arena Exchange
layer. A refused operator-packet import preserves the verified upstream
completion review while retaining no operator decision or packet authority.

### Remaining protected boundary

This local packet does not approve, make a commit decision, commit or adopt a
blueprint, bind rules, qualify, activate, play, execute, register, rank, publish,
spend, or call a provider. Auth, network writes, creator code execution, provider
use, operator commit approval, public activation, and the protected private-alpha
API binding remain separate operator-gated campaigns.

## Review status

- Draft owner: Codex, based on operator direction on 2026-08-30.
- Status: unreviewed hypothesis.
- Required before adoption: provider-diverse refuter, scored review record, and
  explicit owner ruling.
