# Sightline OpenCV 2026 — Stage 1

Sightline is a bounded visual-regression evaluation candidate for the OpenCV AI Competition 2026. This directory implements the first offline slice only: OpenCV output becomes typed findings, deterministic policy turns those findings into a proposed action, and medium/high-risk actions stop for explicit human approval.

## Truth boundary

- No AWS call, account mutation, credit use, deployment, registration, or competition submission occurs here.
- The OpenCV adapter refuses every runtime whose reported major version is not exactly 5.
- The local decision engine never claims that a proposed action was executed.
- Synthetic fixtures and measured OpenCV 5 evidence remain required before the candidate can claim competition qualification.

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

The deterministic policy tests use no network or cloud service. Three generated in-memory fixtures exercise missing-region, unexpected-region, and layout-shift paths through an explicitly labeled OpenCV 5 API test double. This verifies the adapter contract, not OpenCV itself. Re-running the same cases with an official OpenCV 5 build remains required before any OpenCV result is claimed.

## Remaining gates

1. Run the adapter with an exact OpenCV 5 build and record the version plus dependency lock.
2. Re-run the three generated fixture classes with the exact OpenCV 5 build and preserve the receipt.
3. Measure task success, failure handling, and observability without overstating synthetic results.
4. Select and review an inert AWS boundary before any credentialed cloud work.
5. Review the competition's submitted-materials license before any proposal, report, presentation, or video is submitted.
