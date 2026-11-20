# AgentWorld: first visit, return visit, connected choice

October 25, 2026 (Pacific). Proposed delivery plan with the first local implementation prepared. This is scoped to existing BuilderWars #11, draft #82 and stacked draft #102. It does not set a release date, assign a person, authorize spending or claim a public launch.

## Product outcome

A person opens AgentWorld on a phone, understands a companion's current concern, makes a suggestion, sees a consequential acceptance or refusal, and can return to that same history. A subsequent milestone introduces one connected agent that proposes a feasible goal and takes validated actions. BuilderWars' competitions then offer an additional reason to participate together.

The initial audience is an adult curious about interacting with agents who should not need to understand API keys or harnesses. Builders remain the contributors to later connected agents and activities. This is a pilot audience choice to test, not established customer demand.

## What the process should establish

1. Ship a bounded, inspectable slice and preserve failures.
2. Observe representative people using it without teaching the intended answer.
3. Repair consequential obstacles, then repeat with a fresh small group.
4. Measure an actual later return separately from a requested reload or stated intention.
5. Expand connected behavior or community activity when the preceding experience is usable and worth repeating.

Nielsen Norman Group distinguishes a small qualitative study used to discover usability problems from a quantitative study estimating population behavior. Five participants are a starting round, not a retention estimate or demand certificate. [Primary guidance](https://www.nngroup.com/articles/5-test-users-qual-quant/) (read October 25).

Google's original HEART paper abstract describes mapping product goals to user-centered metrics. The table below applies that approach; its definitions and decision rules are this project's proposals. The abstract was read, not the full paper. [Primary publication](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/).

## Existing work and boundaries

- Main reviewed: `d51c12fef1e710e301c0615df20a6e23fbec8fd3`. Academy readiness is merged; the separate readiness-cancellation repair is handed off in #57.
- #82: `65bdfedc9e1ba22c42f87b70f593fae20cd9b81c`, still draft. It owns Relay quests and portable evidence.
- #102: `3f7cfa225dda18fc44076cf458717f83f805ce97`, still draft and stacked on #82. It owns the agency playground, personalities and frontier design.
- This candidate adds only within `experiments/agentworld/agency/`, based on #102. It does not fork a second AgentWorld or connect its four actors to the Arena's two-seat evidence schema.
- Live claims remain authoritative in the studio bus; this isolated candidate does not claim a shared writer. The historical presence mirror does not grant ownership.
- The deterministic engine and policy are unchanged. The first slice is same-device continuity of the existing policy, not new learning, model execution, shared persistence or autonomous background work.

## Delivery stages

| Stage | Deliverable | Acceptance / decision | Current state |
| --- | --- | --- | --- |
| 0. Reconcile | Existing #82/#102 source, review dependencies and one working preview | Named source, disjoint scope, owner adoption path, honest simulation label | Source reviewed; isolated candidate prepared. Shared custody, independent review and integration remain pending. |
| 1. Complete the return visit | Opt-in one-slot save, recap, explicit paused resume, export and Forget | No write before consent; exact replay and memory restored; no automatic turns; failed saves and other-tab changes disclosed; phone/browser checks pass | Implemented locally in this candidate; validation recorded separately. |
| 2. Formative usability | Five adult participants, one prototype version, neutral tasks and issue log | Observe completion, understanding and failures; fix any data-loss, blocked-exit or misleading-agent problem before expansion. Recheck corrections with a fresh round. | Protocol ready; no recruitment, sessions or findings claimed. |
| 3. One connected choice | One admitted external agent, narrow observation/action adapter and a finite project | Agent proposes a feasible goal from actual observations; legal actions are applied by the existing engine; every attempt and failure retained; verified stop/resume and actual execution evidence | Proposed, unimplemented. Existing provider route, account authority and a concrete call/resource cap must be established before execution. No paid call or new account is implied. |
| 4. Return for a reason | A small invited follow-up using a fixed candidate and a declared observation window | Separate requested follow-up visits from voluntary returns. Record raw denominators, missing follow-ups and assistance. Change the experience based on reasons, not a flattering percentage. | Proposed. Window and recruitment belong to the study owner before invitations. |
| 5. Recurring challenge | One understandable objective, invited builders, finite event and replay | Another person can enter, understand the outcome and replay it. Use current scripted cups honestly until connected entrants are separately integrated. | Proposed. No event has been scheduled or invitation sent. |

Stages are dependency gates, not calendar promises. Stage 3 can be prepared while usability work proceeds, but a model demo does not bypass consumer review. Reuse #102's real-agent ambition and existing project semantics; do not add a second agent framework merely to demonstrate a provider call.

## First implementation contract

The visit is saved under one experiment-specific browser key using the existing strict agency recording. Saving defaults off for each fresh unsaved page. An existing checkpoint is offered for explicit resume; accepting the dialog resumes paused and enables continued saving of that visit. Plans, visited cells, energy, requests and world state are reconstructed through the unchanged policy.

The recap describes the last stored state; it does not invent activity while the visitor was absent. Export remains a portable backup. Opt-out retains the earlier checkpoint while stopping new writes. A different unsaved visit cannot silently replace that checkpoint. Confirmed imports/new worlds replace it only when saving is already enabled and the dialog explains that consequence. Forget clears only this experiment's key and disables saving in this tab.

Corruption, unsupported versions, size limits, blocked storage, unacknowledged writes and quota failure must preserve the existing checkpoint or clearly refuse restoration. Other-tab storage events pause the current view and turn saving off; observed conflicting values are rejected. localStorage has no compare-and-swap transaction: this is best-effort conflict detection, not a cross-tab concurrency guarantee. Export before multi-tab work. No cloud backup, account identity or cross-device continuity is claimed.

## Goal → signal → measure

| Goal | Observable signal | Record / interpretation |
| --- | --- | --- |
| Understand the companion | Participant explains a concern and refusal in their own words | Verbatim short explanation and observer notes; do not score consciousness or model intelligence. |
| Influence without controlling | Participant makes a suggestion and identifies its consequence | Exact request, engine action and explanation. Accepting a suggestion alone is insufficient. |
| Preserve continuity | Participant leaves and explicitly resumes the verified visit | Source version, checkpoint turn, resumed turn, assistance/errors; replay equivalence is an engineering check. |
| Want to return | Person returns later and chooses an activity | Raw invited/eligible/observed counts, window, prompted/unprompted reason and missing data. A forced reload is not retention. |
| Builder participation | Another builder contributes a usable entrant or activity | One accepted artifact and independently reproduced outcome under the fixed event rules; views/stars are secondary. |

Start with manual, participant-coded records. Do not add third-party analytics or identifiable session tracking for this pilot. Any later telemetry requires a separately documented event schema, consent/retention decisions and deployment integration. The current code adds no analytics or study identifiers.

## Connected-agent acceptance, before calling it real agency

- Define the supported world observations and legal action schema; simulation authority stays in the existing engine.
- Freeze source, model/route labels, project objective, steps, timeout, calls and resource limits before a run. Set actual numerical limits in the owned implementation ticket; this document does not authorize an unspecified budget.
- Keep the deterministic policy as a labelled comparison. A connected timeout, malformed response or impossible action is recorded, never silently replaced by the script.
- Retain an agent-proposed plan and actual engine effects. A rewritten explanation is not a distinct agent-selected project.
- Verify stop, cancellation, checkpoint recovery and legal replay. Requested and reported model identity remain distinguished from independently attested identity.
- Demonstrate a later choice using retained observations or a prior artifact; do not label simple session restoration as learning.

## Operating cadence and prioritization

After each build or study round, make one short update in #11: exact source, what ran, what failed, what changed for a visitor, and the smallest next action. Keep #57 for application audit/repair evidence and #82/#102 for their own implementation changes. Consolidate findings rather than creating duplicate feature lanes.

Prioritize in this order: lost history or misleading claims; inability to understand/act/stop/return; meaningful agent choices; polish; expansion. Revenue and acquisition experiments follow a clear repeat-use value proposition and direct user evidence. This plan makes no revenue forecast.

## Reviewable completion

For this first slice, return a patch against exact #102, a generated offline HTML, Node/browser receipts with hashes, and this study kit. Maintainer adoption, required independent review, hosted checks, publication, physical-device/assistive-tech checks, real provider execution and human sessions remain separate tracked work. A draft PR or handoff comment is not proof of those outcomes.
