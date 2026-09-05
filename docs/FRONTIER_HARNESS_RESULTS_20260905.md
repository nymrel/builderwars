# Phase 2: versioned local improvement workflow

September 5, 2026. Owner: Codex/Astra. Implementation and local validation complete;
integration/CI receipt belongs in the PR. This is not whole-game strength proof,
base-model training, a web release, or completion of the frontier campaign.

## Measured outcome

Two fresh, private-seeded campaigns used the same source fingerprint, Node22.22.0,
32 training cases,16 development cases, two reserved16-case final suites, and
eight practice passes at rate0.2/margin0.1. Exactly one candidate and one final
evaluation were run per game. No final-case payload or sampler seed was read by
the owner, exposed to the optimizer, or copied into this report. No provider calls.

Errors below are missed wins plus avoidable immediate losses, baseline to candidate.

| Game | Training /32 | Development /16 | Final /16 | Final seat errors | Decision |
| --- | --- | --- | --- | --- | --- |
| Tic-tac-toe | 9 to0 | 0 to0 | 4 to0 | 3 to0;1 to0 | Tactical pass only; retain incumbent |
| Connect Four | 7 to3 | 6 to3 | 6 to3 | 3 to1;3 to2 | Tactical fail; retain incumbent |

All measured moves were legal and all cases assessed. No missed wins occurred.
Final seat counts were8/8 and6/10 respectively. Development tic-tac-toe had13/3
seat coverage and no defense opportunity for seat1: do not infer balanced strength
from that zero. Training made354 and976 pairwise numeric updates. Practice plus
development used10644 and31017 counted work units; final evaluation used996 and3423.
These counts are algorithmic work units, not equal-time/provider-token benchmarks.

The immutable rollback records still select both original incumbents. Remaining
attempt2 and final suites are unused; do not grind them for a favorable result.
Before a source-changing next phase, retire these campaigns and preserve the
store-wide reservations. Private payloads remain local under live-arena/output/frontier/vault.
Public aggregate receipts and full digests are in
[FRONTIER_HARNESS_EVIDENCE_20260905.json](FRONTIER_HARNESS_EVIDENCE_20260905.json).
This small finite sample has no asserted population bound or general-strength lift.

## Review, attribution and resolution

Fable architecture advice requested stronger partitioning, aggregate-only final
outputs and identity/source checks at every phase; those controls were implemented.
Its initial prose response lacked provider-resolved identity metadata. A subsequent
full-code review exceeded its bounded five-minute window and was stopped with no
usable verdict; its usage is unknown. It was not counted as approval.

One narrower retry reviewed FrontierStore and openVersionSession only. Provider
response resolved claude-fable-5-1, session e112f15c-ce9a-4891-99d6-b314285ce227,
verdict APPROVED. It checked exclusive reservations, final-read ordering, candidate
and plan binding, identity checks, discarded late responses and honest status.
It assumed case/practice parsers and did not run tests. Reported duration158486ms;
main input2, cache creation16659, output11671 including10640 thinking tokens.
Reported list cost USD0.925355 includes a Haiku helper; this is not an incremental
subscription-billing receipt. Owner follow-ups snapshot caller options and execute
the sealed plan, clarify that retirement prevents new work without killing an
in-flight bounded operation, and allow historical status/retirement after upgrades
while rejecting execution under changed source. Tests cover these distinctions.

Gemini/Antigravity separately reviewed frontier-cases and frontier-practice, static
and read-only. Consult peer-antigravity-20260905T200101Z-52c664766b, prompt digest
6e9692aaa0156b57fc0b663005acab0e1c8eb12d103b09c72913d4d22f08396d,
requested route gemini-3.1-pro-high; wrapper reported PASS for response format,
not for code. Provider-resolved identity/usage were unavailable. Original verdict:
REJECTED, alleging shared prefixes and private historical-prefix overlap violated
partition separation. That verdict is preserved, not relabeled as approval.

Owner disposition: both findings assume disjoint entire trajectories, which the
contract does not assert. Every legal history includes the same empty opening;
rejecting all prefix intersections would make any nonempty campaign impossible.
Training/development public prefixes cannot contain any reserved final target.
Final evaluated target groups cannot be public or reused across suites/campaigns.
Private final prefixes may overlap; only aggregate final results are returned,
and the optimizer never receives final histories. Existing cross-campaign tests
verify the public/reserved exclusions. A new regression assertion explicitly
shows shared empty openings coexist with valid held-out targets. Documentation
now states the non-disjoint-trajectory limitation. No claimed global/pretraining
novelty and no unaddressed target-exposure example was supplied by this review.
No additional review loop was opened merely to seek a different verdict.

Fable's warning that matching a tactical referee is not independent evidence of
broad playing strength is accepted. Every tactical admission remains explicitly
promotion=not-authorized, including the passing tic-tac-toe candidate.

## Validation and next gate

179/179 local tests pass; TypeScript and Vite build pass. The referee hash remains
d5135878ce69345f5e8ee214c03d53cd1593052b9bcb97d1a96363f9b6dfa823 and the browser
entry bundle remains index-DAHsmVZF.js. Existing policy schema and bridge behavior
are unchanged. The bridge still drops version metadata; do not call it attested.

Next: preregister matched-budget, both-seat full-game evaluation against frozen
nonrandom opponents, quantify uncertainty and veto tactical/seat regressions.
Tic-tac-toe and Connect Four are two connect-game recipes, not evidence of two
distinct game families. Phase3 still needs a genuinely different supported family.
UX/provider adapters, exact public web adoption and the four-family exhibition
remain later work. The earlier four-model charter remains under review; this
bounded implementation does not silently promote its draft strategy.
