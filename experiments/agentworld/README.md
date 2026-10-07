# BuilderWars Agentworld Lab — Relay Commons v0.1

**Status: Relay Commons merged to `main` on 2026-10-05 through [PR #75](https://github.com/nymrel/builderwars/pull/75), merge `9ff2ea338a5e6af687b888bec52541ac9eaf48b1`, after independent source review. Hive memory and its review repairs are tracked in [PR #76](https://github.com/nymrel/builderwars/pull/76). This remains an isolated experiment without a production lab route, hosted rooms, connected providers, or ranking admission.**

## Product hypothesis

Keep BuilderWars as the product. Agentworld is a proposed shared-environment lab inside it: builders bring actors or teams into a persistent environment, observe cooperation and competition, then inspect decisions and replay what happened. This is a working interpretation, not a recovered or approved Agentworld specification. No separate public brand, provider product, or model is being adopted.

Relay Commons tests the smallest usable loop: start a seeded world, watch four scripted actors deliver supplies, take a manual turn, inspect the journal, export a replay, and verify it from the seed. All four actors inhabit one browser simulation. This is **not** multiplayer or a persistent server.

## Run locally

No application dependencies, package installation, API keys, or model calls are required.

```sh
cd experiments/agentworld
python -m http.server 8765 --bind 127.0.0.1
# Open http://127.0.0.1:8765/ in an authorized browser.
node --test test.mjs
```

To generate a portable, self-contained HTML preview:

```sh
python build_preview.py
```

The preview embeds the exact engine, ledger, and app scripts in dependency order and adds their SHA-256 hashes to its content-security policy. Use `--output /path/to/preview.html` to choose another output file. No CDN, font download, analytics, network call, or external code execution is included. File-viewer support for JavaScript and local storage varies; a normal browser on an authorized local origin is the intended full validation environment.

## Consumer quests

The existing page now presents Renay's three cooperative objectives: Find the supplies, Bring help home, and Finish together. Progress is reconstructed from accepted replay events, including on a saved visit's return. An explicit Stop button pauses watching. Capped runs keep earlier milestones and leave the final objective incomplete; crew-comparison runs do not earn cooperative quests. See [the consumer slice and remaining work](CONSUMER_DEMO.md).

Run the added projector checks together with the engine and Hive ledger:

```sh
node --test test.mjs consumer-quests.test.mjs
```

## Rules

The world is an 8 × 8 grid with two crews and four actors. Turns alternate in the frozen order Amber 01, Tide 01, Amber 02, Tide 02. Actors can share cells. Eight supply caches hold sixteen total supplies, with rotationally symmetric placement determined by a nonzero 32-bit seed.

An actor can move one orthogonal cell within the grid, collect one supply on its cell when empty, deliver a carried supply at its own base, or wait. Only the actor for the current turn may act. Illegal actions do not consume a turn or change state. The world ends when all supplies are delivered or when 240 accepted turns are reached. The cap is an incomplete result, not automatic success.

Cooperative mode reports a shared delivery goal. Crew-comparison mode displays the same per-crew counts as an **unranked, single-run comparison**, not a balanced evaluation. The fixed turn order and scripted tie-breaks have not been accepted as a fair competitive protocol. Balanced seeds, swapped seats, frozen budgets and independent review remain required before any comparative research or ranking claim.

## Agent contract

`engine.js` exposes `Agentworld.create`, `active`, `legal`, `step`, `scripted`, `pack`, `parse` and `verify`. Callers must obtain state through `create` or verified replay; arbitrary caller-supplied state is not a security boundary. A future hosted service must own state and authorize actors server-side.

```json
{"turn":0,"actor":"amber-1","source":"manual","type":"move","direction":"east"}
```

Actions require exact fields. A move additionally requires direction; other actions forbid it. Allowed sources are `scripted` and `manual`, both **self-declared metadata**. Source labels do not authenticate a human, model, provider or execution environment. Observation export contains the current public world state and legal actions. There is no public HTTP action endpoint or provider connector in this experiment.

The replay contract contains the version, initial configuration, accepted actions and claimed final state. Import runs every action from the seed and compares the reconstructed state. The strict JSON parser rejects duplicate keys, unsafe/non-integer numbers, oversized input, excessive nesting, unknown schema fields and unsupported actions. Packets are capped at 128 KiB and 240 actions. This is local replay consistency, **not** a signature, origin proof, independent rerun, hosted-execution receipt or ranking admission. Editing an entire valid replay can still produce another valid local replay.

## Hive memory (`ledger.js`)

The hive-memory panel accepts up to 64 selected files and describes their unique verified replay contents: per-actor delivery/collect/move/wait tallies, crew totals, per-run outcomes (seed, mode, outcome, turns), and mode summaries. Every counted replay passes the strict parser and engine reconstruction; actor deliveries must agree with its reconstructed final scores. Oversized files are refused before their contents are read. Duplicate, unreadable, malformed, or invalid entries are listed with reasons while valid companion files can still count. The 64-entry limit includes refused and duplicate files.

Deduplication compares the complete canonical `{config, actions}` content after verification. Renamed or reformatted copies count once, with the smallest bounded filename chosen deterministically as the representative. FNV-1a fingerprints remain non-cryptographic ordering identifiers; a matching fingerprint alone never establishes equality. Different replay contents with colliding fingerprints remain separate. Accepted rows, refusals, and the complete exported aggregate are deterministic under input reordering.

These counts describe unique replay contents, not independently attested execution events. Separate executions with identical configuration and actions cannot be distinguished by this format. Editing a valid replay or changing a self-declared source label does not prove another execution or another actor's identity.

The JavaScript ledger API accepts an array of `{label, text}` entries or `{label, error}` file-read refusals, with an optional string label. Entries cannot contain both `text` and `error`; replay text must be a string. Labels and refusal reasons are bounded to 80 and 160 characters. An error entry can only become a refusal, never an accepted run.

The aggregate is **descriptive, not a ranking**: it says nothing about which actor, crew, strategy, or operator is better. Source labels remain self-declared. It adds no network calls, storage, or provider surface, and exports as `builderwars.agentworld.hive-ledger.v0.1` JSON.

## Browser behavior

Watch, pause, single-step and bounded batch controls use scripted policies. Manual controls and JSON actions are recorded separately. Auto-play pauses when the page is hidden. Live rendering preserves in-progress JSON edits; stale actions fail without mutation. Replay import checks the run revision after asynchronous file reading and requires confirmation before replacing a nonempty run.

Hive builds use a separate generation counter. Every build attempt and file-selection change invalidates older pending work, clears the previous aggregate, and disables its export. A superseded file-read success or error cannot replace the newer result. Export is enabled only after the current selection has produced its displayed aggregate, including any refusal list.

Local saving uses a versioned localStorage key. Restoration verifies the replay before adopting it. Unreadable storage is not overwritten automatically. Storage-change events and a pre-write checkpoint comparison disable saving on detected cross-tab conflicts. These are best-effort local safeguards, not atomic multi-client synchronization. Removal is explicit and turns off automatic saving. Export remains available when storage is unavailable.

## Historical prototype validation (2026-09-20/21)

- Node 22.16.0: **19/19 engine tests passed**, including a 100-seed invariant sweep, replay tampering, duplicate-key rejection, bounds, conservation and terminal behavior.
- Chromium in-memory DOM fixture: **21/21 checks passed**, including 320/390/768/1280 px horizontal-overflow checks, scripted and manual actions, pause, import/export, malformed replay refusal, editor preservation, storage-unavailable behavior, no JavaScript errors, no external requests and readable non-JavaScript rules.
- Local-origin and file navigation were blocked by browser policy with `ERR_BLOCKED_BY_ADMINISTRATOR`. No policy was altered. Actual origin loading, reload persistence, real cross-tab integration, deployment and cross-browser behavior remain **not verified**.
- Screenshot inspection covers the rendered desktop and 390 px mobile fixtures, not physical-device, screen-reader or actual-zoom acceptance.

`browser_test.py` runs the full loopback harness by default. It requires Python Playwright and an installed Chromium executable; adjust its executable path for the reviewer host. `--memory` runs the explicitly narrower fixture suite after `python build_preview.py`. It must not be substituted for full-origin acceptance.

## Integration re-validation (2026-10-03, opencode, claim `opencode-agentworld-relay-commons-20261003`)

Landed onto current `main` (`2361f30`, PR #74) by merge with zero conflicts; engine.js/app.js/index.html byte-identical to the reviewed branch (receipts bind SHA-256). Engine suite 19/19 (`node --test test.mjs`, Node via the reviewer host). First-ever real loopback-origin run of the origin-only checks found two **harness** defects, both fixed in `review_acceptance.py` only: `#proof` is styled `text-transform:uppercase` on a real origin so the rendered-text assertion had to compare case-insensitively, and the cross-tab check's string-argument `wait_for_function` evaluates as page JavaScript, which this experiment's own strict CSP (`script-src 'self'`, no `unsafe-eval`) correctly refuses; it now polls the checkbox from the harness side. After those fixes: real-origin acceptance **11/11 PASS**, controller fixture **8/8 PASS** (`evidence/opencode-*-20261003.json`). The previously blocked-on-policy origin checks (reload persistence, corrupt checkpoint, real same-origin tabs) are now exercised on a loopback origin; screen-reader, physical-device, cross-browser and deployment acceptance remain open.

This October 3 integration was prepared on the PR branch. The actual merge to repository `main` occurred on October 5, as recorded above. Earlier evidence files remain historical receipts for their recorded source hashes.

## Independent landing review and scoped repair (2026-10-05)

PR #75's reviewed head `90176818e97cdfd321cf91100afa7d21f83a674a` passed 19 engine tests and a fresh 11-check real-origin acceptance run before merge. Its exact-head AgentWars integrity workflow and the subsequent merged-main workflow also passed. That hosted workflow covers existing repository contracts; the experiment's Node and browser suites were run separately.

Independent review of PR #76 identified and repaired duplicate counting, order-dependent refusals and fingerprint ties, unbounded file reads, stale asynchronous builds, and the missing ledger script in portable previews. Regression coverage includes two different valid replays with the same FNV fingerprint, whole-aggregate serialization, pre-read refusal, individual read errors, selection/build supersession, and preview import/export under the actual restrictive CSP. Source receipts now include `ledger.js`; controller fixtures load engine, ledger, and app in dependency order.

Fresh repair validation passed **26/26 Node tests**, **16/16 real-origin checks**, **13/13 controller-fixture checks**, and **17/17 generated-preview checks**. Browser runs used Playwright 1.58.0 with Chromium 153.0.8010.0 and reported no page errors, external requests, or CSP violations; the preview additionally made no subresource requests. The separate receipts are `evidence/astra-hive-node-20261005.txt` and `evidence/astra-hive-{origin,fixture,portable}-acceptance-20261005.json`. The browser receipts bind the tested scripts and harness by SHA-256; the preview receipt also binds its builder and generated HTML. These supplement, rather than replace, the original October 3 evidence.

Use `review_acceptance.py --output <new-directory>` for the real-origin suite, add `--controller-fixture` for the explicitly narrower controller mode, or add `--portable-preview` to build and test the self-contained HTML on a real loopback origin. Each run requires a new output directory and preserves earlier evidence. The preview mode tests the generated document without external script files; it does not establish compatibility with arbitrary file viewers.

Reviews are recorded as source-review comments through the authorized GitHub connection. They are independent of the original implementation authoring work, not claims of a distinct GitHub account or cross-model-family approval. Physical-device, screen-reader, actual-zoom, target-mobile-browser, provider, hosted-execution, and deployment acceptance remain outside this source landing.

## Historical integration and coordination

Baseline inspected: `nymrel/builderwars` main `e6bb900d28af4a28d83cef772d25fe9ed5d2f44f` (PR #65). Root README, `.agent/presence.md`, and the BuilderWars ecosystem/audit issues were read. Root AGENTS.md and CLAUDE.md were not present at that pin.

Only a new `experiments/agentworld/` namespace is proposed. Existing live-arena, mobile-arena, referee, provider, CI, branding, historical receipts and presence files remain untouched. No studio bus claim or takeover is asserted: JalenPC was offline and the Studio Knowledge endpoint failed to connect. The old presence mirror is not treated as a current ownership lease.

Related contracts: issues #11 (ecosystem), #16 (identities), #17 (external execution), #18 (creator-game admission), and #57 (usability acceptance). This experiment does not close any of them.

## Next integration gates

1. Confirm the working Agentworld concept and obtain an authoritative, disjoint studio claim. Review this experiment independently before proposing a lab route; do not alter current core acceptance or production release work.
2. Run the full browser harness on an authorized origin. Prove storage recovery, cross-tab behavior, pending-file-read races, keyboard/screen-reader behavior, actual zoom and target mobile browsers. Revalidate exact source after any change.
3. Add a reviewed adapter to BuilderWars' existing observation/action and identity contracts rather than creating a second provider or proof subsystem. Keep scripted and connected-agent runs distinct; attach actual execution evidence separately from replay legality.
4. Only then scope server-authoritative rooms: actor admission, authorization, state revisions, idempotent commands, bounded queues, reconnect recovery, quotas, isolation and privacy. No unknown code execution or hidden provider fallback.
5. Freeze a meaningful experiment before running real agents: equal permissions/budgets, full attempt accounting, repeated seeds and swapped seats, explicit interventions and a non-universal outcome claim. Costs and public release remain separately controlled.

No merge, production deployment, account change, paid inference, public entrant intake, public ranking or autonomous ongoing job is authorized by this prototype.
