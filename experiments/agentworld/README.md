# BuilderWars Agentworld Lab — Relay Commons v0.1

**Status: isolated experimental prototype; not merged, deployed, ranked, or independently reviewed.**

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

The preview embeds the exact scripts and adds their SHA-256 hashes to its content-security policy. No CDN, font download, analytics, network call, or external code execution is included. File-viewer support for JavaScript and local storage varies; a normal browser on an authorized local origin is the intended full validation environment.

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

## Browser behavior

Watch, pause, single-step and bounded batch controls use scripted policies. Manual controls and JSON actions are recorded separately. Auto-play pauses when the page is hidden. Live rendering preserves in-progress JSON edits; stale actions fail without mutation. Replay import checks the run revision after asynchronous file reading and requires confirmation before replacing a nonempty run.

Local saving uses a versioned localStorage key. Restoration verifies the replay before adopting it. Unreadable storage is not overwritten automatically. Storage-change events and a pre-write checkpoint comparison disable saving on detected cross-tab conflicts. These are best-effort local safeguards, not atomic multi-client synchronization. Removal is explicit and turns off automatic saving. Export remains available when storage is unavailable.

## Validation from this implementation session

- Node 22.16.0: **19/19 engine tests passed**, including a 100-seed invariant sweep, replay tampering, duplicate-key rejection, bounds, conservation and terminal behavior.
- Chromium in-memory DOM fixture: **21/21 checks passed**, including 320/390/768/1280 px horizontal-overflow checks, scripted and manual actions, pause, import/export, malformed replay refusal, editor preservation, storage-unavailable behavior, no JavaScript errors, no external requests and readable non-JavaScript rules.
- Local-origin and file navigation were blocked by browser policy with `ERR_BLOCKED_BY_ADMINISTRATOR`. No policy was altered. Actual origin loading, reload persistence, real cross-tab integration, deployment and cross-browser behavior remain **not verified**.
- Screenshot inspection covers the rendered desktop and 390 px mobile fixtures, not physical-device, screen-reader or actual-zoom acceptance.

`browser_test.py` runs the full loopback harness by default. It requires Python Playwright and an installed Chromium executable; adjust its executable path for the reviewer host. `--memory` runs the explicitly narrower fixture suite after `python build_preview.py`. It must not be substituted for full-origin acceptance.

## Integration and coordination

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
