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

These generated fixtures establish reproducibility and failure observability only. They do not establish browser coverage, production accuracy, leaderboard performance, or competition qualification.

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

`.github/workflows/sightline-opencv5.yml` repeats the hash-checked installation on Ubuntu 24.04 with CPython 3.12, verifies `cv2==5.0.0` and `numpy==2.3.5`, runs all 23 tests without skips, compiles every Python module, emits the measured baseline, and builds the deterministic review-only AWS artifact. The workflow has read-only repository permission and no AWS or deployment capability.

## Remaining gates

1. Expand evaluation to a provenance-safe corpus of representative Nymrel-owned or publicly licensed browser screenshots before making any competition-quality claim.
2. Produce judge-safe report, architecture, reproducibility, limitations, and demo materials.
3. Review the competition's Submitted Materials and registration terms against the exact judge-facing package.
4. Credentialed AWS deployment remains blocked until authorized account access is available and no billing, promotional-credit acceptance, or spend is required.
