# Sightline Technical Report — Draft, Not Submitted

## Problem

Visual regressions can leave an application functional at the protocol level while making important controls, content, or layouts unusable. Sightline turns bounded visual evidence into an auditable diagnostic decision without granting the agent authority to modify or deploy an application.

## Approach

Sightline compares a baseline PNG with a candidate PNG using OpenCV 5. It computes an absolute-difference mask, extracts bounded connected components, classifies missing, unexpected, and shifted regions, and normalizes those findings into a deterministic SHA-256 trace.

A policy layer maps the findings to one of three outcomes:

- accept no material change;
- request human approval;
- reject unbounded input.

Medium- and high-risk findings stop at human approval. The current system exposes no repository-write, configuration-change, or deployment tool.

## OpenCV 5 Role

OpenCV 5.0.0 performs image decoding, absolute difference, grayscale conversion, thresholding, connected-component extraction, and PNG fixture encoding. The hosted environment pins the official Python wheel and NumPy by exact version and SHA-256.

## Agentic Loop

1. Perception: OpenCV 5 produces typed visual findings.
2. Decision: deterministic policy selects the next bounded outcome.
3. Control: material changes require human approval.
4. Evidence: the trace records the normalized findings digest and false execution authority.

## Evaluation

The generated offline baseline covers missing-region, unexpected-region, and layout-shift cases. All three expected task outcomes pass. Two fail-closed controls cover unreadable images and dimension mismatch. The merged Stage 1 hosted unit suite contains 35 tests, including pre-decode PNG expansion and dimension-mismatch regressions. The local journey extension adds four demo-approval regressions, for 39 local tests; this extension has not yet received an independent review or merged release.

A separate browser workflow serves tracked Nymrel-owned BuilderWars Mobile Arena source on loopback and evaluates six labeled workflows at fixed 1040×900 desktop and 390×844 mobile viewports independently in managed Chromium and Firefox: a stable Arena, a missing featured receipt, unexpectedly open local-session and proof sheets, and Arena misroutes to Watch and Build. Each browser passes 12/12 outcomes against OpenCV 5.0.0, with 10 true positives, 2 true negatives, zero false positives, and zero false negatives. Across both receipts, all 24 case executions pass with 20 true positives and 4 true negatives. Precision, recall, specificity, and accuracy are each 1.0 within each twelve-case browser set.

The first labeled run exposed an accepted fragmented missing-panel regression. Sightline now stops when aggregate changed area reaches 2% or when eight disconnected components are present; dedicated tests preserve both aggregate and fragmented materiality. The missing receipt requests human approval, while the two changes exceeding 100 findings fail closed as unbounded. The receipt records zero cross-origin requests, zero console warnings/errors, no persisted PNGs, false AWS invocation, and false execution authority.

These results establish deterministic behavior for generated fixtures and six labeled loopback workflow types at two fixed viewports in Chromium and Firefox only. They do not establish public-site capture, user-traffic representativeness, production accuracy, broad browser/device coverage, or generalization.

## AWS-Compatible Boundary

The Lambda-compatible handler accepts two bounded base64 PNG inputs and returns findings plus the decision trace. It performs no network, storage-service, repository, mutation, or deployment action.

A deterministic source builder emits an allowlisted ZIP and passes its metadata through an inert AWS boundary. The boundary rejects credential-bearing environments and requires credential, deployment, and spend authority to remain false. No AWS endpoint has been contacted.

## Reproducibility

The repository documents the hash-locked CPython 3.12 environment, test command, evaluator, AWS artifact builder, synthetic-only demo-bundle builder, and hosted exact-head evidence. The generated artifact uses fixed timestamps, permissions, ordering, and content. The deterministic private demo bundle contains only three generated PNG pairs, a machine-readable evaluation, the tracked architecture SVG, and a SHA-256 manifest; its receipt excludes local paths and denies execution, publication, and submission authority. The judge packet includes a self-contained SVG architecture rendering; the verifier parses it as XML and rejects scripts, foreign objects, embedded images, event handlers, doctypes/entities, links, and external CSS URLs.

## Responsible Operation

Inputs are size-bounded and must be PNG. Invalid base64, unreadable images, dimension mismatch, excessive findings, unsafe artifact metadata, credentials, and deployment authority fail closed. Secret values are never emitted by the AWS-boundary checks.

## Current Limitations

The corpus combines generated arrays with six labeled loopback workflow types at two fixed viewports in Chromium and Firefox; it remains too small to represent browser traffic, devices, broad browser coverage, responsive breakpoints, or production conditions. The classifier is intentionally narrow. No AWS deployment, production endpoint, user study, or competition submission has occurred. See `LIMITATIONS.md` for the complete claim boundary.

## Measured End-to-End Demonstration

The 167.72-second English-captioned local recording uses the actual tracked BuilderWars Arena. It compares the normal view with a controlled hidden featured receipt. Real OpenCV 5.0.0 produces 54 retained connected components and 62,432 changed pixels; the unchanged policy requests human approval. A restore without approval is rejected and the screenshot remains byte-identical.

A separate demonstration controller then consumes one candidate-bound approval event to restore only the injected DOM visibility property. The event is explicitly labeled `automated_demo_operator`, with `human_approval_observed=false` and no production authority. It illustrates a control boundary; it does not establish actual human approval, production authentication, or general autonomous repair. The planner itself retains false execution authority.

After restoration, a fresh screenshot is byte-identical to the original baseline and a new OpenCV pass returns zero findings. This verifies this one known injected fault at a 1040x900 viewport. The fault injection supplies the cause; pixel evidence alone does not diagnose an unknown root cause.

The recording retains actual malformed-PNG, dimension-mismatch and oversized-IHDR rejections. Earlier fragmented-materiality false negatives, mobile below-fold framing errors, reversed fixture polarity and the repaired compressed-PNG expansion vulnerability remain in the evidence record.

Source lineage: Stage 1 merge `c41a83d5761dd98edf1d776686555e21ba4803b9`; current-main base `1745c0a0cc8aaa31aaf8f67edc7765f32de6b547`; local recording revision `e46cc424229beb2d4b138772b6d56f374582be85`. The retained receipt contains exact source-file and input hashes. A current-main Firefox 146.0.1 rerun passes 12/12 controlled cases. Historical Chromium evidence is retained as historical, not represented as a fresh current-main rerun.

## Delivery Status - October 24, 2026

Meaningful AWS execution, judge endpoint or arranged screen share, public/unlisted video hosting, live Devpost form/terms review, and final submission remain unverified. No AWS account was mutated, billing changed, credits accepted, or paid compute started. The execution environment has no AWS CLI/profile/credential access; the available browser returned Site Unavailable for the AWS console. The Devpost connection requires reauthentication. These are access blockers, not successful deployments or evidence of an unsubmitted authenticated project.

The documentation, source, controlled evidence and local video can be reviewed now. A candidate CloudShell runbook is preparation only: CloudShell has no additional service charge, but AWS documents standard data-transfer charges and charges for other services. Account access, permitted cost envelope and real execution must be verified before running. No end-to-end time saving, detection uplift against a simpler baseline, production benefit, cloud cost or cloud latency has been measured.
