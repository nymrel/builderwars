# Sightline OpenCV 2026 — Stage 1

Sightline is a bounded visual-regression evaluation candidate for the OpenCV AI Competition 2026. This directory implements an offline-first slice: OpenCV output becomes typed findings, deterministic policy turns those findings into a proposed action, and medium/high-risk actions stop for explicit human approval.

## Truth boundary

- No AWS call, account mutation, credit use, deployment, registration, or competition submission occurs here.
- The OpenCV adapter refuses every runtime whose reported major version is not exactly 5.
- The decision engine never claims that a proposed action was executed.
- The adapter has been exercised against the official OpenCV 5.0.0 Python wheel in a hash-checked Linux x86_64 / CPython 3.12 environment. This is narrow adapter evidence, not competition qualification.

## Stage 1 contract

`OpenCV5Perception.analyze_files()` loads a baseline and candidate image, computes a binary absolute-difference mask, extracts bounded connected components, and returns typed `VisualFinding` records. `SightlineAgent.plan()` then returns one of:

- `accept_no_material_change`
- `request_human_approval`
- `reject_unbounded_input`

Every trace includes a deterministic digest of the normalized findings. The engine cannot execute a deployment or mutate a product surface.

## Local validation

```bash
python -m unittest discover -s evaluations/sightline-opencv-2026 -p 'test_*.py'
```

The deterministic policy tests use no network or cloud service. Three generated in-memory fixtures exercise missing-region, unexpected-region, and layout-shift paths through an explicitly labeled OpenCV 5 API test double.

The same fixture classes are covered by `test_opencv5_integration.py` against the exact dependencies in `requirements-opencv5-linux-x86_64-py312.txt`:

```bash
python -m pip install --require-hashes \
  -r evaluations/sightline-opencv-2026/requirements-opencv5-linux-x86_64-py312.txt
python -m unittest discover \
  -s evaluations/sightline-opencv-2026 -p 'test_*.py'
```

## Measured offline baseline

`evaluate_stage1.py` runs a deterministic generated-fixture baseline against the pinned real OpenCV runtime:

- 3/3 expected finding classifications and policy outcomes passed.
- 2/2 fail-closed controls passed.
- Every material case returned `request_human_approval`.
- Every case reported `execution_authorized=false` and `aws_invoked=false`.
- The JSON receipt includes deterministic input and trace SHA-256 digests and exits nonzero if any check fails.

These generated fixtures establish reproducibility and failure observability only. They do not establish production accuracy, leaderboard performance, or competition qualification.

## Browser-rendered controlled corpus

`evaluate_browser_corpus.py` serves tracked Nymrel-owned `mobile-arena/` source on loopback and captures four labeled Chromium workflows: a stable Arena, a missing featured receipt, an unexpectedly open local-session sheet, and an Arena-to-Watch misroute. The temporary PNGs are evaluated through the exact OpenCV 5 adapter and deleted when the process exits.

The current labeled corpus reports 4/4 correct outcomes, 3 true positives, 1 true negative, zero false positives, and zero false negatives. Precision, recall, specificity, and accuracy are each 1.0 on this four-case set. The missing-receipt case exposed and now regression-tests fragmented visual materiality: eight or more disconnected low-area components stop for approval even when no single component reaches 2% of the viewport. Larger changes that exceed 100 findings fail closed as unbounded.

The receipt binds the repository head, source path, browser/runtime versions, viewport, each PNG SHA-256, and each findings digest. It fails on wrong outcomes, cross-origin requests, console warnings/errors, persisted PNGs, AWS invocation, or execution authority. This is labeled loopback evidence on a real tracked surface; it is not public-site capture, user traffic, or a production-accuracy claim.

## Inert AWS boundary

`aws_boundary.py` prepares a reviewable AWS Lambda plan without importing an AWS SDK, loading credentials, or exposing an execution method. It:

- requires credential, deployment, and spend authority to remain false;
- rejects common credential-bearing AWS environment variables without logging values;
- allows only bounded artifact names, exact lowercase SHA-256 digests, packages no larger than 50 MiB, and an explicit region allowlist;
- emits `operation=prepare_only`, `execute=false`, and false credential/deployment/spend authority fields.

## Lambda-compatible local path

`aws_lambda_handler.py` accepts two bounded base64 PNG inputs, runs the real OpenCV 5 adapter and decision policy, and returns typed findings plus the decision trace. It has no network, storage-service, repository, or deployment operation.

`build_aws_artifact.py` creates a deterministic, allowlisted source ZIP with fixed timestamps and permissions, then hashes it and passes its metadata through the inert boundary:

```bash
python evaluations/sightline-opencv-2026/build_aws_artifact.py \
  --output-dir /tmp/sightline-artifact
```

The artifact is neither uploaded nor deployed. A successful receipt must report `artifact_uploaded=false`, `network_invoked=false`, `operation=prepare_only`, and all authority fields false.

## Hosted validation

`.github/workflows/sightline-opencv5.yml` repeats the hash-checked installation on Ubuntu 24.04 with CPython 3.12, verifies `cv2==5.0.0` and `numpy==2.3.5`, runs all 29 tests without skips, compiles every Python module, emits the measured baseline, builds the deterministic review-only AWS artifact, and verifies the draft judge packet. The workflow has read-only repository permission and no AWS or deployment capability.

`.github/workflows/sightline-browser-corpus.yml` separately installs pinned Playwright 1.58.0 and managed Chromium, renders tracked BuilderWars source only over loopback, and runs the browser corpus without uploading the temporary PNGs.

## Judge-facing preparation

The private draft packet contains:

- technical report;
- architecture and trust boundaries;
- limitations and claim boundary;
- sub-five-minute demo script;
- official-terms and registration matrix; and
- official submission-requirements traceability.

The packet verifier hashes an exact allowlist, rejects unexpected or sensitive content, and always reports `draft_not_submitted`, `publication_authorized=false`, and `submission_authorized=false`.

## Remaining gates

1. Expand beyond the current four labeled Nymrel-owned workflows across more routes, viewport classes, and provenance-cleared states before making any competition-quality claim.
2. Demonstrate a meaningful component actually running on AWS; local Lambda compatibility and an inert plan are not AWS execution.
3. Render and review judge-facing assets using only cleared fixtures, then freeze the exact Submitted Materials corpus.
4. Monitor for the final controlling Devpost terms and organizer reconciliation of the deadline and reward conflicts.
5. Credentialed AWS deployment remains blocked until authorized account access is available and no billing, promotional-credit acceptance, or spend is required.
