# Sightline OpenCV 2026 — Stage 1

Sightline is a bounded visual-regression evaluation candidate for the OpenCV AI Competition 2026. This directory implements the first offline slice only: OpenCV output becomes typed findings, deterministic policy turns those findings into a proposed action, and medium/high-risk actions stop for explicit human approval.

## Truth boundary

- No AWS call, account mutation, credit use, deployment, registration, or competition submission occurs here.
- The OpenCV adapter refuses every runtime whose reported major version is not exactly 5.
- The local decision engine never claims that a proposed action was executed.
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

The deterministic policy tests use no network or cloud service. Three generated in-memory fixtures exercise missing-region, unexpected-region, and layout-shift paths through an explicitly labeled OpenCV 5 API test double. This verifies the dependency-free adapter contract independently from the real-runtime integration suite.

The same three fixture classes are also covered by `test_opencv5_integration.py` against the exact dependencies in `requirements-opencv5-linux-x86_64-py312.txt`. Install them in an isolated CPython 3.12 environment with hash checking:

```bash
python -m pip install --require-hashes \
  -r evaluations/sightline-opencv-2026/requirements-opencv5-linux-x86_64-py312.txt
python -m unittest \
  evaluations/sightline-opencv-2026/test_opencv5_integration.py
```

## Measured offline baseline

`evaluate_stage1.py` runs a deterministic, generated-fixture baseline against the pinned real OpenCV runtime. It measures the narrow Stage 1 contract without making a real-world quality claim:

- 3/3 expected finding classifications and policy outcomes passed: missing region, unexpected region, and layout shift.
- 2/2 fail-closed controls passed: unreadable input and dimension mismatch.
- Every material case returned `request_human_approval`.
- Every case reported `execution_authorized=false` and `aws_invoked=false`.
- The JSON receipt includes deterministic input and trace SHA-256 digests and exits nonzero if any check fails.

Run it only after the hash-checked dependency installation above:

```bash
python evaluations/sightline-opencv-2026/evaluate_stage1.py
```

These generated fixtures establish reproducibility and failure observability only. They do not establish browser coverage, production accuracy, leaderboard performance, or competition qualification.

## Inert AWS boundary

`aws_boundary.py` prepares a reviewable AWS Lambda deployment plan without importing an AWS SDK, loading credentials, or exposing an execution method. It is intentionally incapable of deployment.

The boundary:

- requires credential, deployment, and spend authority to remain false;
- rejects common credential-bearing AWS environment variables without logging their values;
- allows only bounded artifact names, exact lowercase SHA-256 digests, packages no larger than 50 MiB, and an explicit region allowlist;
- emits `operation=prepare_only`, `execute=false`, and false credential/deployment/spend authority fields.

This closes design-time review of the inert boundary only. Credentialed AWS work still requires authorized account access and confirmation that no billing, promotional-credit acceptance, or spend is involved.

## Hosted validation

`.github/workflows/sightline-opencv5.yml` repeats the exact hash-checked installation on Ubuntu 24.04 with CPython 3.12, verifies `cv2==5.0.0` and `numpy==2.3.5`, runs all 18 tests without skips, compiles every Python module, and emits the measured offline-baseline JSON. The workflow has read-only repository permission and no AWS or deployment capability.

## Remaining gates

1. Expand the evaluation beyond generated fixtures to representative real-world or browser screenshots before making any competition-quality claim.
2. Package and exercise the inert AWS interface locally without credentials; credentialed deployment remains separately gated.
3. Review the competition's submitted-materials license against the exact judge-facing package before submission.
