# Sightline Requirements Traceability — Draft, Not Submitted

Official-source snapshot: 2026-09-24 UTC.

Sources:

- Overview and submission requirements: https://opencv26.devpost.com/
- Rules and judging rubric: https://opencv26.devpost.com/rules

Status vocabulary:

- **Implemented** — present in the exact private draft branch with passing tests.
- **Prepared** — draft material exists but is not published or submitted.
- **Partial** — some evidence exists but the organizer's complete requirement is not yet met.
- **Blocked** — requires a capability or authorization outside the current fail-closed boundary.
- **Not pursued** — optional category intentionally excluded from current claims.

## Core eligibility and deliverables

| Organizer requirement | Exact evidence | Status | Remaining proof |
|---|---|---|---|
| Substantive OpenCV 5 image or video analysis | `OpenCV5Perception` uses OpenCV 5.0.0 for decoding, absolute difference, grayscale conversion, thresholding, and connected-component extraction; official wheels are hash-locked in hosted CI and four labeled BuilderWars workflows run in Chromium. | **Implemented** | Broaden the small provenance-cleared workflow corpus across routes and viewport classes. |
| Meaningful component running on AWS | Lambda-compatible handler, deterministic source artifact, and inert AWS plan exist. The plan explicitly has no credentials, upload, execution, deployment, or spend authority. | **Partial** | A real AWS deployment and evidence are still required; local compatibility is not AWS execution. |
| Technical report | `TECHNICAL_REPORT.draft.md` covers problem, users, architecture, OpenCV role, AWS boundary, evaluation, limitations, and responsible operation. | **Prepared** | Reconcile with final measured corpus and actual AWS evidence. |
| Judge-accessible repository or archive | Private draft PR and deterministic review-only source ZIP exist. | **Partial** | Freeze the exact authorized corpus and establish judge access without exposing excluded private assets. |
| Pinned dependencies and build/deploy/test instructions | OpenCV 5.0.0 and NumPy 2.3.5 wheels are hash-locked; local and hosted test/build commands are documented. | **Implemented** for local validation | Add real deployment instructions only after an authorized, zero-spend AWS path exists. |
| Architecture diagram | `ARCHITECTURE.draft.md` traces PNG inputs, OpenCV perception, typed findings, policy, human approval, evidence digest, Lambda handler, and inert AWS plan. | **Prepared** | Replace the inert AWS box with verified runtime evidence if deployment occurs. |
| Working endpoint or arranged live screen-share | No endpoint is deployed and no demonstration session is arranged. | **Blocked** | Requires an authorized deployment or later organizer coordination; do not claim availability. |
| Public or unlisted video no longer than five minutes | A 4:30 draft script exists with recording safeguards. | **Partial** | Record only with provenance-cleared fixtures after the exact Submitted Materials scope is authorized. |
| Evaluation including failure cases or limitations | Generated baseline passes 3/3 task cases and 2/2 fail-closed controls. Four labeled loopback Chromium workflows pass 4/4 with 3 true positives, 1 true negative, zero false positives, and zero false negatives; precision, recall, specificity, and accuracy are 1.0 on this small set. Limitations are explicit. | **Partial** | Broaden the four-case corpus across more Nymrel-owned routes, states, and viewport classes before making a competition-quality claim. |

## Agentic Vision category

| Qualifying evidence | Exact evidence | Status | Remaining proof |
|---|---|---|---|
| OpenCV output changes a later decision, action, tool call, or human-approval request | Typed findings deterministically change the policy outcome; material findings produce `request_human_approval`. | **Implemented** |
| Workflow diagram | Architecture draft shows perception → decision → human approval and evidence trace. | **Prepared** |
| Trace or demonstration | Deterministic finding digest and decision trace exist in tests and evaluator receipts. | **Implemented** for generated fixtures |
| Task effectiveness | 3/3 generated cases and 4/4 labeled browser workflows pass. The browser confusion matrix has zero false positives and zero false negatives on four cases. | **Partial** — the corpus remains too small and controlled for a competition-quality claim. |
| Failure handling and observability | Unreadable input and dimension mismatch fail closed; receipts expose false execution/AWS authority. | **Implemented** for current boundary |
| Appropriate human control | Medium/high-risk findings stop for approval; no mutation or deployment tool exists. | **Implemented** |

Sightline currently appears aligned with the Agentic Vision mechanism because visual findings alter a later human-approval request. This is a technical inference from the published category language, not an organizer eligibility determination.

## Optional COOL category

Sightline does not currently claim the Best Use of COOL Award. No COOL integration, AWS Graviton execution, Arm benchmark, or corresponding cost/performance evidence exists. Status: **Not pursued**.

## Judging-weight readiness

| Criterion | Weight | Current evidence | Primary gap |
|---|---:|---|---|
| Technical execution | 30% | Exact OpenCV 5 runtime, typed findings, aggregate/fragmented materiality guards, deterministic traces, bounded handler, 29 passing hosted tests, and a digest-bound labeled Chromium corpus. | Broader representative-workflow performance and deployed AWS evidence. |
| Innovation | 20% | Perception-to-auditable-decision loop with explicit no-execution authority. | Comparative positioning and demonstrated iteration beyond a narrow pixel-difference baseline. |
| Real-world impact | 20% | Clear visual-regression problem and human-control model. | User evidence, representative workflows, and measured benefit. |
| User experience | 10% | Typed results and explicit approval state. | Judge-visible interface or live demonstration. |
| Documentation and presentation | 10% | Draft report, architecture, limitations, demo script, terms matrix, and this traceability matrix. | Final rendered assets and recorded demonstration. |
| Cloud delivery, reproducibility, responsible operation | 10% | Hash-locked runtime, deterministic artifact, credential/spend guards, fail-closed tests. | Actual AWS deployment, runtime observability, latency/cost evidence, and reproducible deployment instructions. |

## Fail-closed conclusion

The current private branch is a reproducible Stage 1 implementation, not a competition-ready submission. The two largest technical gaps are:

1. a broader representative-workflow browser evaluation beyond the current four labeled loopback cases; and
2. meaningful, verified AWS execution without spending, billing activation, promotional-credit acceptance, or unauthorized credentials.

Registration, terms acceptance, publication, deployment, and submission remain disabled. The packet remains **Draft, Not Submitted**.
