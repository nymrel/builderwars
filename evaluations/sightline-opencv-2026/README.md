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

## Remaining gates

1. Reproduce the hash-checked OpenCV 5 integration suite in hosted CI.
2. Measure task success, failure handling, and observability without overstating synthetic results.
3. Select and review an inert AWS boundary before any credentialed cloud work.
4. Review the competition's submitted-materials license before any proposal, report, presentation, or video is submitted.
